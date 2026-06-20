"""Historical long-term statistics import helpers for Yorkshire Water."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
import functools
from pathlib import Path
import re
from typing import Any, Literal
from zoneinfo import ZoneInfo

from .api import YorkshireWaterEndpointNotConfiguredError, YorkshireWaterSchemaError
from .const import DEFAULT_CUMULATIVE_USAGE_ENTITY_ID, DOMAIN

SERVICE_IMPORT_STATISTICS = "import_statistics"

CONF_ALLOW_OVERWRITE = "allow_overwrite"
CONF_DRY_RUN = "dry_run"
CONF_END_DATE = "end_date"
CONF_ENTITY_ID = "entity_id"
CONF_FILE_PATH = "file_path"
CONF_SOURCE = "source"
CONF_START_DATE = "start_date"

SOURCE_API = "api"
SOURCE_CSV = "csv"

STATISTIC_UNIT = "m³"

_DATE_ROW = re.compile(r"^(?P<day>\d{1,2})(?:\s+\w+)?$")
_MONTH_FORMATS = ("%B %Y", "%b %Y")
_CURRENCY_PREFIXES = ("£", "GBP")


class YorkshireWaterStatisticsImportError(ValueError):
    """Raised when historical statistics import data is not safe to import."""


@dataclass(frozen=True, kw_only=True)
class DailyUsageRow:
    """One complete day of historical Yorkshire Water usage."""

    day: date
    litres: float
    clean_water_cost: float | None = None
    total_cost: float | None = None

    @property
    def cubic_metres(self) -> float:
        """Return the usage in cubic metres."""
        return self.litres / 1000


@dataclass(frozen=True, kw_only=True)
class ImportStatisticsPlan:
    """Prepared statistics import data."""

    daily_rows: list[DailyUsageRow]
    statistics: list[dict[str, Any]]
    base_cumulative_m3: float
    base_sum_m3: float
    first_imported_cumulative_m3: float
    final_cumulative_m3: float
    final_sum_m3: float
    existing_statistics_overlap: bool
    overlap_count: int
    overlap_start_date: date | None
    overlap_end_date: date | None
    base_strategy: str
    monotonic_validation_passed: bool
    negative_dashboard_deltas_avoided: bool


def parse_yorkshire_water_csv(text: str) -> list[DailyUsageRow]:
    """Parse a Yorkshire Water CSV export into daily usage rows."""
    reader = csv.reader(text.splitlines())
    rows = list(reader)
    month_start = _parse_csv_month(rows)

    daily_rows: list[DailyUsageRow] = []
    seen_dates: set[date] = set()
    declared_total_litres: float | None = None

    for row in rows:
        if not row:
            continue
        first_cell = row[0].strip()
        if not first_cell:
            continue
        if first_cell.lower() == "total":
            declared_total_litres = _parse_litres(row[1] if len(row) > 1 else "")
            continue
        if first_cell.lower() == "date":
            continue
        match = _DATE_ROW.match(first_cell)
        if not match:
            continue

        if len(row) < 2:
            raise YorkshireWaterStatisticsImportError(
                "CSV daily row is missing a litres value"
            )
        day_number = int(match.group("day"))
        try:
            row_day = month_start.replace(day=day_number)
        except ValueError as err:
            raise YorkshireWaterStatisticsImportError(
                "CSV daily row date is outside the declared month"
            ) from err
        if row_day in seen_dates:
            raise YorkshireWaterStatisticsImportError(
                "CSV contains duplicate daily rows"
            )
        seen_dates.add(row_day)

        daily_rows.append(
            DailyUsageRow(
                day=row_day,
                litres=_parse_litres(row[1]),
                clean_water_cost=_parse_optional_cost(row[2] if len(row) > 2 else None),
                total_cost=_parse_optional_cost(row[3] if len(row) > 3 else None),
            )
        )

    if not daily_rows:
        raise YorkshireWaterStatisticsImportError("CSV did not contain daily usage rows")

    daily_rows.sort(key=lambda item: item.day)
    if declared_total_litres is not None:
        actual_total = round(sum(row.litres for row in daily_rows), 3)
        if round(declared_total_litres, 3) != actual_total:
            raise YorkshireWaterStatisticsImportError(
                "CSV total litres does not match the daily rows"
            )

    return daily_rows


def daily_rows_from_api_periods(periods: list[dict[str, Any]]) -> list[DailyUsageRow]:
    """Build daily import rows from normalized API daily periods."""
    rows: list[DailyUsageRow] = []
    seen_dates: set[date] = set()
    for period in periods:
        row_day = _coerce_date(period.get("start") or period.get("start_date"))
        if row_day in seen_dates:
            raise YorkshireWaterStatisticsImportError(
                "API returned duplicate daily rows"
            )
        seen_dates.add(row_day)

        litres = period.get("value_litres")
        if litres is None and period.get("value_m3") is not None:
            litres = float(period["value_m3"]) * 1000
        rows.append(
            DailyUsageRow(
                day=row_day,
                litres=_parse_litres(litres),
                clean_water_cost=_parse_optional_cost(period.get("clean_water_cost")),
                total_cost=_parse_optional_cost(period.get("total_cost")),
            )
        )

    if not rows:
        raise YorkshireWaterStatisticsImportError("API returned no daily usage rows")
    rows.sort(key=lambda item: item.day)
    return rows


def validate_daily_rows(
    rows: list[DailyUsageRow],
    *,
    latest_known_date: date,
) -> None:
    """Validate daily rows before dry-run or import."""
    if not rows:
        raise YorkshireWaterStatisticsImportError("No daily usage rows to import")
    seen_dates: set[date] = set()
    today = date.today()
    for row in rows:
        if row.day in seen_dates:
            raise YorkshireWaterStatisticsImportError(
                "Daily import contains duplicate dates"
            )
        seen_dates.add(row.day)
        if row.litres < 0:
            raise YorkshireWaterStatisticsImportError(
                "Daily import contains negative litres"
            )
        if row.day > latest_known_date:
            raise YorkshireWaterStatisticsImportError(
                "Daily import contains dates newer than the latest known Yorkshire Water data"
            )
        if row.day >= today:
            raise YorkshireWaterStatisticsImportError(
                "Daily import only supports complete historical days"
            )


def build_cumulative_statistics_rows(
    rows: list[DailyUsageRow],
    *,
    timezone: ZoneInfo,
    base_cumulative_m3: float = 0,
    base_sum_m3: float = 0,
) -> list[dict[str, Any]]:
    """Build cumulative statistics rows from daily usage rows.

    The first statistic row is the opening meter-like value at the first
    imported day. Each source day then advances the cumulative value at the
    next local midnight, allowing daily Energy Dashboard deltas to be derived
    from boundary-to-boundary increases.
    """
    ordered = sorted(rows, key=lambda item: item.day)
    if not ordered:
        return []

    current_state = float(base_cumulative_m3)
    current_sum = float(base_sum_m3)
    statistics: list[dict[str, Any]] = [
        {
            "start": _local_midnight(ordered[0].day, timezone),
            "state": round(current_state, 6),
            "sum": round(current_sum, 6),
        }
    ]
    for row in ordered:
        current_state += row.cubic_metres
        current_sum += row.cubic_metres
        statistics.append(
            {
                "start": _local_midnight(row.day + timedelta(days=1), timezone),
                "state": round(current_state, 6),
                "sum": round(current_sum, 6),
            }
        )
    return statistics


def build_import_statistics_plan(
    rows: list[DailyUsageRow],
    *,
    timezone: ZoneInfo,
    prior_stats: list[dict[str, Any]] | None = None,
    overlapping_stats: list[dict[str, Any]] | None = None,
    future_stats: list[dict[str, Any]] | None = None,
    live_state_m3: float | None = None,
    allow_overwrite: bool = False,
    block_overlap: bool = True,
) -> ImportStatisticsPlan:
    """Build an import plan from source rows and existing recorder statistics."""
    prior_stats = prior_stats or []
    overlapping_stats = overlapping_stats or []
    future_stats = future_stats or []
    overlap_start, overlap_end = _overlap_date_range(
        overlapping_stats,
        timezone=timezone,
    )
    if overlapping_stats and block_overlap and not allow_overwrite:
        raise YorkshireWaterStatisticsImportError(
            _overlap_error_message(
                requested_start=rows[0].day,
                requested_end=rows[-1].day,
                overlap_count=len(overlapping_stats),
                overlap_start=overlap_start,
                overlap_end=overlap_end,
            )
        )

    total_m3 = sum(row.cubic_metres for row in rows)
    base_cumulative_m3, base_sum_m3, base_strategy = _select_import_baseline(
        total_m3=total_m3,
        prior_stats=prior_stats,
        overlapping_stats=overlapping_stats,
        future_stats=future_stats,
        live_state_m3=live_state_m3,
    )

    statistics = build_cumulative_statistics_rows(
        rows,
        timezone=timezone,
        base_cumulative_m3=base_cumulative_m3,
        base_sum_m3=base_sum_m3,
    )
    _validate_statistics_rows(statistics)
    _validate_existing_statistic_joins(
        rows=statistics,
        future_stats=future_stats,
    )
    return ImportStatisticsPlan(
        daily_rows=rows,
        statistics=statistics,
        base_cumulative_m3=base_cumulative_m3,
        base_sum_m3=base_sum_m3,
        first_imported_cumulative_m3=float(statistics[1]["state"])
        if len(statistics) > 1
        else float(statistics[0]["state"]),
        final_cumulative_m3=float(statistics[-1]["state"]),
        final_sum_m3=float(statistics[-1]["sum"]),
        existing_statistics_overlap=bool(overlapping_stats),
        overlap_count=len(overlapping_stats),
        overlap_start_date=overlap_start,
        overlap_end_date=overlap_end,
        base_strategy=base_strategy,
        monotonic_validation_passed=True,
        negative_dashboard_deltas_avoided=True,
    )


def build_dry_run_report(
    *,
    source: str,
    statistic_id: str,
    plan: ImportStatisticsPlan,
) -> dict[str, Any]:
    """Build a safe service response for dry runs and completed imports."""
    rows = plan.daily_rows
    total_litres = round(sum(row.litres for row in rows), 3)
    return {
        "source": source,
        "statistic_id": statistic_id,
        "requested_import_start_date": rows[0].day.isoformat(),
        "requested_import_end_date": rows[-1].day.isoformat(),
        "daily_rows_parsed": len(rows),
        "statistics_rows_prepared": len(plan.statistics),
        "earliest_date": rows[0].day.isoformat(),
        "latest_date": rows[-1].day.isoformat(),
        "total_litres": total_litres,
        "total_m3": round(total_litres / 1000, 6),
        "baseline_strategy": plan.base_strategy,
        "baseline_m3": round(plan.base_cumulative_m3, 6),
        "base_cumulative_m3": round(plan.base_cumulative_m3, 6),
        "first_imported_cumulative_m3": round(
            plan.first_imported_cumulative_m3,
            6,
        ),
        "final_cumulative_m3": round(plan.final_cumulative_m3, 6),
        "monotonic_validation_passed": plan.monotonic_validation_passed,
        "negative_dashboard_deltas_avoided": plan.negative_dashboard_deltas_avoided,
        "existing_statistics_overlap": plan.existing_statistics_overlap,
        "overlap_detected": plan.existing_statistics_overlap,
        "overlap_count": plan.overlap_count,
        "overlapping_start_date": plan.overlap_start_date.isoformat()
        if plan.overlap_start_date
        else None,
        "overlapping_end_date": plan.overlap_end_date.isoformat()
        if plan.overlap_end_date
        else None,
        "overlapping_statistic_count": plan.overlap_count,
        "allow_overwrite_would_allow_import": plan.existing_statistics_overlap,
        "overwrite_behaviour": "recorder_import_updates_matching_statistic_timestamps_only",
        "base_strategy": plan.base_strategy,
    }


def build_import_statistics_service_schema() -> Any:
    """Build the Home Assistant schema for the import_statistics service."""
    from homeassistant.const import CONF_ENTITY_ID as HA_CONF_ENTITY_ID
    import homeassistant.helpers.config_validation as cv
    import voluptuous as vol

    return vol.Schema(
        {
            vol.Optional(
                HA_CONF_ENTITY_ID,
                default=DEFAULT_CUMULATIVE_USAGE_ENTITY_ID,
            ): cv.entity_id,
            vol.Required(CONF_SOURCE): vol.In((SOURCE_API, SOURCE_CSV)),
            vol.Optional(CONF_START_DATE): cv.date,
            vol.Optional(CONF_END_DATE): cv.date,
            vol.Optional(CONF_FILE_PATH): cv.string,
            vol.Optional(CONF_DRY_RUN, default=True): cv.boolean,
            vol.Optional(CONF_ALLOW_OVERWRITE, default=False): cv.boolean,
        }
    )


async def async_handle_import_statistics(
    hass: Any,
    call: Any,
) -> dict[str, Any]:
    """Handle the Yorkshire Water historical statistics import service."""
    from homeassistant.const import CONF_ENTITY_ID as HA_CONF_ENTITY_ID
    from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

    data = dict(call.data)
    entity_id = data.get(HA_CONF_ENTITY_ID, DEFAULT_CUMULATIVE_USAGE_ENTITY_ID)
    source = data[CONF_SOURCE]
    dry_run = data.get(CONF_DRY_RUN, True)
    allow_overwrite = data.get(CONF_ALLOW_OVERWRITE, False)

    _safe_import_log(
        hass,
        "Yorkshire Water statistics import started: source=%s dry_run=%s allow_overwrite=%s",
        source,
        dry_run,
        allow_overwrite,
    )

    try:
        rows = await _async_load_daily_rows(hass, source, data)
        _safe_import_log(
            hass,
            "Yorkshire Water statistics import parsed rows: count=%s",
            len(rows),
        )
        latest_known_date = _latest_known_yorkshire_water_date(hass, entity_id)
        validate_daily_rows(rows, latest_known_date=latest_known_date)
        plan = await _async_prepare_import_plan(
            hass,
            entity_id,
            rows,
            allow_overwrite=allow_overwrite,
            block_overlap=not dry_run,
        )
        report = build_dry_run_report(
            source=source,
            statistic_id=entity_id,
            plan=plan,
        )
        report["dry_run"] = dry_run
        report["allow_overwrite"] = allow_overwrite
        if dry_run:
            report["imported_statistics_rows"] = 0
            _safe_import_log(
                hass,
                (
                    "Yorkshire Water statistics dry run complete: "
                    "rows=%s total_litres=%s final_cumulative_m3=%s "
                    "baseline_strategy=%s baseline_m3=%s "
                    "monotonic=%s negative_deltas_avoided=%s "
                    "overlap=%s overlap_start=%s overlap_end=%s overlap_count=%s "
                    "allow_overwrite_would_allow_import=%s"
                ),
                len(rows),
                report["total_litres"],
                report["final_cumulative_m3"],
                report["baseline_strategy"],
                report["baseline_m3"],
                report["monotonic_validation_passed"],
                report["negative_dashboard_deltas_avoided"],
                plan.existing_statistics_overlap,
                report["overlapping_start_date"],
                report["overlapping_end_date"],
                plan.overlap_count,
                report["allow_overwrite_would_allow_import"],
            )
            return report

        await _async_import_statistics_rows(hass, entity_id, plan.statistics)
        report["imported_statistics_rows"] = len(plan.statistics)
        _safe_import_log(
            hass,
            "Yorkshire Water statistics import complete: daily_rows=%s statistics_rows=%s",
            len(rows),
            len(plan.statistics),
        )
        return report
    except YorkshireWaterStatisticsImportError as err:
        raise ServiceValidationError(str(err)) from err
    except YorkshireWaterEndpointNotConfiguredError as err:
        raise ServiceValidationError(str(err)) from err
    except YorkshireWaterSchemaError as err:
        raise ServiceValidationError(str(err)) from err
    except HomeAssistantError:
        raise


def _safe_import_log(hass: Any, message: str, *args: Any) -> None:
    """Log import progress without sensitive identifiers."""
    logger = hass.data.get(DOMAIN, {}).get("statistics_import_logger")
    if logger is not None:
        logger.info(message, *args)


async def _async_load_daily_rows(
    hass: Any,
    source: Literal["api", "csv"],
    data: dict[str, Any],
) -> list[DailyUsageRow]:
    """Load import source rows without exposing sensitive inputs."""
    if source == SOURCE_CSV:
        file_path = data.get(CONF_FILE_PATH)
        if not file_path:
            raise YorkshireWaterStatisticsImportError("CSV import requires file_path")
        text = await hass.async_add_executor_job(Path(file_path).read_text)
        return parse_yorkshire_water_csv(text)

    start_date = data.get(CONF_START_DATE)
    end_date = data.get(CONF_END_DATE)
    if start_date is None or end_date is None:
        raise YorkshireWaterStatisticsImportError(
            "API import requires start_date and end_date"
        )
    if start_date > end_date:
        raise YorkshireWaterStatisticsImportError(
            "API import start_date must be on or before end_date"
        )
    return await _async_fetch_api_daily_rows(hass, start_date, end_date)


async def _async_fetch_api_daily_rows(
    hass: Any,
    start_date: date,
    end_date: date,
) -> list[DailyUsageRow]:
    """Fetch API daily rows from the configured Yorkshire Water entry."""
    entry_data = _first_entry_data(hass)
    api = entry_data.get("api")
    if api is None:
        raise YorkshireWaterEndpointNotConfiguredError(
            "Yorkshire Water API is not configured"
        )

    await api.async_ensure_valid_token()
    meter_reference = api.meter_reference
    move_in_date: date | str = start_date
    move_out_date: date | str = end_date
    if not meter_reference and api.account_reference:
        meter_payload = await api.async_get_meter_details(api.account_reference)
        meters = meter_payload.get("meters", [])
        if meters:
            meter_reference = meters[0].get("meter_reference")
            move_in_date = meters[0].get("start_date") or start_date
            move_out_date = meters[0].get("end_date") or end_date

    if not meter_reference:
        raise YorkshireWaterEndpointNotConfiguredError(
            "Yorkshire Water meter reference is not configured yet"
        )

    summary = await api.async_get_daily_consumption(
        meter_reference,
        start_date=start_date,
        end_date=end_date,
        move_in_date=move_in_date,
        move_out_date=move_out_date,
    )
    return daily_rows_from_api_periods(summary["daily_periods"])


async def _async_prepare_import_plan(
    hass: Any,
    statistic_id: str,
    rows: list[DailyUsageRow],
    *,
    allow_overwrite: bool,
    block_overlap: bool = True,
) -> ImportStatisticsPlan:
    """Prepare validated cumulative statistics rows."""
    timezone = ZoneInfo(getattr(hass.config, "time_zone", None) or "UTC")
    base_start = _local_midnight(rows[0].day, timezone)
    import_end = _local_midnight(rows[-1].day + timedelta(days=1), timezone)

    prior_stats, overlapping_stats, future_stats = await _async_get_existing_statistics(
        hass,
        statistic_id,
        base_start,
        import_end,
    )
    return build_import_statistics_plan(
        rows,
        timezone=timezone,
        prior_stats=prior_stats,
        overlapping_stats=overlapping_stats,
        future_stats=future_stats,
        live_state_m3=_live_state_m3(hass, statistic_id),
        allow_overwrite=allow_overwrite,
        block_overlap=block_overlap,
    )


async def _async_get_existing_statistics(
    hass: Any,
    statistic_id: str,
    import_start: datetime,
    import_end: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return prior, overlapping, and future recorder statistics."""
    from homeassistant.components.recorder import statistics
    from homeassistant.util import dt as dt_util

    earliest = datetime(1970, 1, 1, tzinfo=UTC)
    import_start_utc = dt_util.as_utc(import_start)
    import_end_utc = dt_util.as_utc(import_end + timedelta(seconds=1))
    future_start_utc = dt_util.as_utc(import_end + timedelta(seconds=1))
    statistic_ids = {statistic_id}
    types = {"state", "sum"}

    prior = await hass.async_add_executor_job(
        functools.partial(
            statistics.statistics_during_period,
            hass,
            earliest,
            import_start_utc,
            statistic_ids,
            "hour",
            None,
            types,
        )
    )
    overlap = await hass.async_add_executor_job(
        functools.partial(
            statistics.statistics_during_period,
            hass,
            import_start_utc,
            import_end_utc,
            statistic_ids,
            "hour",
            None,
            types,
        )
    )
    future = await hass.async_add_executor_job(
        functools.partial(
            statistics.statistics_during_period,
            hass,
            future_start_utc,
            None,
            statistic_ids,
            "hour",
            None,
            types,
        )
    )
    return (
        prior.get(statistic_id, []),
        overlap.get(statistic_id, []),
        future.get(statistic_id, []),
    )


async def _async_import_statistics_rows(
    hass: Any,
    statistic_id: str,
    rows: list[dict[str, Any]],
) -> None:
    """Import prepared rows into Home Assistant recorder statistics."""
    from homeassistant.components.recorder import statistics
    from homeassistant.components.recorder.const import DOMAIN as RECORDER_DOMAIN
    from homeassistant.components.recorder.models import StatisticMeanType

    metadata = {
        "has_mean": False,
        "mean_type": StatisticMeanType.NONE,
        "has_sum": True,
        "name": "Yorkshire Water Estimated Cumulative Usage",
        "source": RECORDER_DOMAIN,
        "statistic_id": statistic_id,
        "unit_class": "volume",
        "unit_of_measurement": STATISTIC_UNIT,
    }
    statistics.async_import_statistics(hass, metadata, rows)


def _latest_known_yorkshire_water_date(hass: Any, entity_id: str) -> date:
    """Return the latest date this integration should import up to."""
    latest_dates: list[date] = []
    for value in _entries(hass).values():
        coordinator = value.get("coordinator")
        data = getattr(coordinator, "data", None) or {}
        if latest := data.get("latest_data_date"):
            try:
                latest_dates.append(_coerce_date(latest))
            except YorkshireWaterStatisticsImportError:
                pass
    if latest_dates:
        return max(latest_dates)
    return date.today() - timedelta(days=1)


def _entries(hass: Any) -> dict[str, Any]:
    """Return configured Yorkshire Water entry data mappings."""
    return {
        key: value
        for key, value in hass.data.get(DOMAIN, {}).items()
        if isinstance(value, dict) and "api" in value
    }


def _first_entry_data(hass: Any) -> dict[str, Any]:
    """Return the first configured Yorkshire Water entry data mapping."""
    entries = _entries(hass)
    if not entries:
        raise YorkshireWaterEndpointNotConfiguredError(
            "Yorkshire Water integration is not configured"
        )
    return next(iter(entries.values()))


def _select_import_baseline(
    *,
    total_m3: float,
    prior_stats: list[dict[str, Any]],
    overlapping_stats: list[dict[str, Any]],
    future_stats: list[dict[str, Any]],
    live_state_m3: float | None,
) -> tuple[float, float, str]:
    """Select a baseline that keeps imported statistics monotonic."""
    if prior_stats:
        prior_state, prior_sum = _statistic_cumulative_pair(
            _latest_statistic(prior_stats)
        )
        return prior_state, prior_sum, "prior_statistic"

    if future_stats:
        future_state, future_sum = _statistic_cumulative_pair(
            _earliest_statistic(future_stats)
        )
        base_state = future_state - total_m3
        base_sum = future_sum - total_m3
        if base_state < 0 or base_sum < 0:
            raise YorkshireWaterStatisticsImportError(
                "Unable to align import with future statistics without a negative baseline"
            )
        return base_state, base_sum, "future_statistic_backfill"

    if live_state_m3 is not None:
        base_state = live_state_m3 - total_m3
        if base_state < 0:
            raise YorkshireWaterStatisticsImportError(
                "Unable to align import with live state without a negative baseline"
            )
        return base_state, base_state, "live_state_baseline"

    if overlapping_stats:
        overlap_state, overlap_sum = _statistic_cumulative_pair(
            _earliest_statistic(overlapping_stats)
        )
        return overlap_state, overlap_sum, "prior_statistic"

    return 0.0, 0.0, "zero_baseline"


def _statistic_cumulative_pair(stat: dict[str, Any]) -> tuple[float, float]:
    """Return state and sum values from a statistics row, falling back safely."""
    state = _coerce_optional_statistic_float(stat.get("state"))
    total = _coerce_optional_statistic_float(stat.get("sum"))
    if state is None and total is None:
        raise YorkshireWaterStatisticsImportError(
            "Existing statistics row is missing state and sum values"
        )
    if state is None:
        state = total
    if total is None:
        total = state
    return float(state), float(total)


def _coerce_optional_statistic_float(value: Any) -> float | None:
    """Coerce an optional statistics value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as err:
        raise YorkshireWaterStatisticsImportError(
            "Existing statistics row contains a non-numeric cumulative value"
        ) from err


def _live_state_m3(hass: Any, entity_id: str) -> float | None:
    """Return the current live cumulative sensor state when available."""
    states = getattr(hass, "states", None)
    if states is None:
        return None
    state_obj = states.get(entity_id)
    if state_obj is None:
        return None
    try:
        return float(state_obj.state)
    except (TypeError, ValueError):
        return None


def _validate_statistics_rows(rows: list[dict[str, Any]]) -> None:
    """Validate prepared recorder rows before import."""
    previous_start: datetime | None = None
    previous_state: float | None = None
    previous_sum: float | None = None
    for row in rows:
        start = row["start"]
        if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
            raise YorkshireWaterStatisticsImportError(
                "Prepared statistics contain a naive timestamp"
            )
        state = float(row["state"])
        total = float(row["sum"])
        if state < 0 or total < 0:
            raise YorkshireWaterStatisticsImportError(
                "Prepared statistics contain a negative cumulative value"
            )
        if previous_start is not None and start <= previous_start:
            raise YorkshireWaterStatisticsImportError(
                "Prepared statistics are not chronological"
            )
        if previous_state is not None and state < previous_state:
            raise YorkshireWaterStatisticsImportError(
                "Prepared statistics are not cumulative"
            )
        if previous_sum is not None and total < previous_sum:
            raise YorkshireWaterStatisticsImportError(
                "Prepared statistics sums are not cumulative"
            )
        previous_start = start
        previous_state = state
        previous_sum = total


def _validate_existing_statistic_joins(
    *,
    rows: list[dict[str, Any]],
    future_stats: list[dict[str, Any]],
) -> None:
    """Validate that generated rows do not step down into future statistics."""
    if not rows or not future_stats:
        return
    final_state = float(rows[-1]["state"])
    final_sum = float(rows[-1]["sum"])
    future_state, future_sum = _statistic_cumulative_pair(
        _earliest_statistic(future_stats)
    )
    if final_state > future_state or final_sum > future_sum:
        raise YorkshireWaterStatisticsImportError(
            "Generated statistics would create a negative dashboard delta to existing future statistics"
        )


def _earliest_statistic(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the earliest statistics row by start date when available."""
    return min(
        stats,
        key=lambda stat: _statistic_start_datetime_utc(stat)
        or datetime.max.replace(tzinfo=UTC),
    )


def _latest_statistic(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the latest statistics row by start date when available."""
    return max(
        stats,
        key=lambda stat: _statistic_start_datetime_utc(stat)
        or datetime.min.replace(tzinfo=UTC),
    )


def _statistic_start_datetime_utc(stat: dict[str, Any]) -> datetime | None:
    """Extract a UTC datetime from a Home Assistant statistics row."""
    value = stat.get("start")
    if value is None:
        return None
    if isinstance(value, datetime):
        start = value
    elif isinstance(value, date):
        start = datetime.combine(value, time.min)
    elif isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    elif isinstance(value, str):
        try:
            start = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
        start = start.replace(tzinfo=UTC)
    return start.astimezone(UTC)


def _overlap_date_range(
    overlapping_stats: list[dict[str, Any]],
    *,
    timezone: ZoneInfo,
) -> tuple[date | None, date | None]:
    """Return the safe date range for overlapping statistics."""
    dates = [
        stat_date
        for stat in overlapping_stats
        if (stat_date := _statistic_start_date(stat, timezone=timezone)) is not None
    ]
    if not dates:
        return None, None
    return min(dates), max(dates)


def _statistic_start_date(
    stat: dict[str, Any],
    *,
    timezone: ZoneInfo,
) -> date | None:
    """Extract a date from a Home Assistant statistics row."""
    start = _statistic_start_datetime_utc(stat)
    if start is None:
        return None
    return start.astimezone(timezone).date()


def _overlap_error_message(
    *,
    requested_start: date,
    requested_end: date,
    overlap_count: int,
    overlap_start: date | None,
    overlap_end: date | None,
) -> str:
    """Build a safe overlap error message without identifiers or secrets."""
    return (
        "Existing statistics overlap the requested import range "
        f"{requested_start.isoformat()} to {requested_end.isoformat()}; "
        f"overlapping_start_date={overlap_start.isoformat() if overlap_start else 'unknown'}; "
        f"overlapping_end_date={overlap_end.isoformat() if overlap_end else 'unknown'}; "
        f"overlapping_statistic_count={overlap_count}. "
        "Run with dry_run: true to review the overlap, then use "
        "allow_overwrite: true only if you intend to update matching statistics rows."
    )


def _parse_csv_month(rows: list[list[str]]) -> date:
    """Parse the Yorkshire Water CSV time period header."""
    for row in rows:
        if not row:
            continue
        if row[0].strip().lower() != "time period:":
            continue
        if len(row) < 2 or not row[1].strip():
            break
        value = row[1].strip()
        for fmt in _MONTH_FORMATS:
            try:
                return datetime.strptime(value, fmt).date().replace(day=1)
            except ValueError:
                continue
        break
    raise YorkshireWaterStatisticsImportError("CSV is missing a valid Time Period header")


def _parse_litres(value: Any) -> float:
    """Parse and validate a litres value."""
    try:
        litres = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError) as err:
        raise YorkshireWaterStatisticsImportError(
            "Daily import contains a non-numeric litres value"
        ) from err
    if litres < 0:
        raise YorkshireWaterStatisticsImportError(
            "Daily import contains negative litres"
        )
    return litres


def _parse_optional_cost(value: Any) -> float | None:
    """Parse optional future cost-statistics fields without blocking import."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for prefix in _CURRENCY_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _coerce_date(value: Any) -> date:
    """Coerce a date-like value to date."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError as err:
            raise YorkshireWaterStatisticsImportError(
                "Daily import contains an invalid date"
            ) from err
    raise YorkshireWaterStatisticsImportError("Daily import contains an invalid date")


def _local_midnight(day: date, timezone: ZoneInfo) -> datetime:
    """Return a timezone-aware local midnight for a date."""
    return datetime.combine(day, time.min, tzinfo=timezone)
