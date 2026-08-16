# Yorkshire Water - Home Assistant Integration

A custom Home Assistant integration for Yorkshire Water smart meter usage.

This integration is being adapted for Yorkshire Water's customer portal. The Home Assistant integration identity and architecture are in place, and the provider-specific API layer is isolated for Yorkshire Water endpoint discovery.

## Current Status

- Home Assistant domain: `yorkshire_water`
- Component folder: `custom_components/yorkshire_water`
- Integration name: Yorkshire Water
- Repository: `https://github.com/Crash-Evans/ha_yorkshire_water`
- API status: beta manual bearer token mode plus experimental OAuth PKCE token exchange foundation for captured smart meter endpoints

This is a new Home Assistant integration/domain. Add Yorkshire Water as a fresh integration.

## Sensors

The initial Yorkshire Water sensor set is intentionally practical:

| Sensor | Entity ID pattern | Unit |
| --- | --- | --- |
| Yesterday Usage | `sensor.yorkshire_water_yesterday_usage` | L |
| Today Usage | `sensor.yorkshire_water_today_usage` | L |
| 7-Day Average | `sensor.yorkshire_water_7_day_average` | L |
| Week to Date | `sensor.yorkshire_water_week_to_date` | L |
| Previous Week | `sensor.yorkshire_water_previous_week` | L |
| Month to Date | `sensor.yorkshire_water_month_to_date` | L |
| Year to Date | `sensor.yorkshire_water_year_to_date` | L |
| Meter Reading | `sensor.yorkshire_water_meter_reading` | m³ |
| Estimated Cumulative Usage | `sensor.yorkshire_water_estimated_cumulative_usage` | m³ |
| Yesterday Cost | `sensor.yorkshire_water_yesterday_cost` | GBP |
| Today Cost | `sensor.yorkshire_water_today_cost` | GBP |
| Week to Date Cost | `sensor.yorkshire_water_week_to_date_cost` | GBP |
| Previous Week Cost | `sensor.yorkshire_water_previous_week_cost` | GBP |
| Month to Date Cost | `sensor.yorkshire_water_month_to_date_cost` | GBP |
| Year to Date Cost | `sensor.yorkshire_water_year_to_date_cost` | GBP |
| Continuous Flow Alarm | `sensor.yorkshire_water_continuous_flow_alarm` | diagnostic |
| Data Latest Update Status | `sensor.yorkshire_water_data_latest_update_status` | diagnostic |
| Status | `sensor.yorkshire_water_status` | diagnostic |

Usage values are normalized to litres. Attributes include source period start/end, latest data date, latest update date, estimated and missing day counts, available cost breakdown fields, raw period data when available, data freshness, and whether the meter reading is estimated.

If the temporary bearer token or required account/meter references are missing, the integration stays in endpoint discovery mode and exposes a status message instead of making live requests.

## Home Assistant Energy Dashboard

Home Assistant's Energy Dashboard water section needs a cumulative water sensor with `device_class: water` and `state_class: total_increasing`. Period sensors such as Yesterday Usage, Week to Date, Month to Date, and Year to Date are useful for daily monitoring, but they reset or change with the reporting period and should not be added to the Energy Dashboard.

Use `sensor.yorkshire_water_estimated_cumulative_usage` for Energy Dashboard water consumption. It reports cubic metres and is estimated from the usage totals available from Yorkshire Water, not from an official physical meter-reading endpoint. If a later API response contains less usage than a previous refresh, the integration preserves the previous cumulative value so the sensor remains monotonic.

To add it, open Settings -> Dashboards -> Energy -> Water consumption, then select Estimated Cumulative Usage.

## Importing historical usage

Home Assistant does not automatically backfill old Energy Dashboard water usage from the current sensor state. Yorkshire Water provides an `import_statistics` service to import historical usage into long-term statistics for `sensor.yorkshire_water_estimated_cumulative_usage`.

This service imports statistics for the cumulative m³ water sensor only. It does not import history for Yesterday Usage, Week to Date, Month to Date, Year to Date, or other period sensors.

Always run a dry run first. Dry runs are the default and return the number of daily rows parsed, earliest and latest dates, total litres, final cumulative m³, and whether existing statistics overlap the requested range.

### CSV export import

Export the monthly CSV from Yorkshire Water, place it somewhere Home Assistant can read, then call:

```yaml
service: yorkshire_water.import_statistics
data:
  source: csv
  file_path: /config/yorkshire-water/june-2026.csv
  dry_run: true
```

If the dry-run totals and overlap status look correct, run the same service with `dry_run: false`. Set `allow_overwrite: true` only when you intentionally want Home Assistant's recorder import to update matching statistic rows in the same date range. The service does not purge the whole date range; it imports the prepared cumulative rows and lets the recorder update rows with the same statistic start timestamp while leaving other existing rows alone.

The CSV parser reads the `Time Period:` month/year header, imports daily `Date,Litres` rows, ignores the `Total` row for daily statistics, and validates that the total litres match the daily rows. Costs are parsed opportunistically for future cost-statistics support, but cost parsing does not block water usage import.

### API date-range import

For historical data still available from the Yorkshire Water daily-consumption endpoint, call:

```yaml
service: yorkshire_water.import_statistics
data:
  source: api
  start_date: "2026-06-01"
  end_date: "2026-06-30"
  dry_run: true
```

The API import uses the configured Yorkshire Water account and meter references. It converts daily litres to cumulative m³ statistics in chronological order.

### Cumulative base strategy

When importing a partial month or an older date range, the integration continues from the last prior statistic for the cumulative sensor if one exists. If no prior statistic exists, it starts the first imported boundary row at `0` m³ and then increases by each imported daily usage amount.

Statistics rows are written at local day boundaries so the Energy Dashboard can calculate daily consumption from cumulative increases. Today and future dates are rejected because historical imports should contain complete daily usage only.

After an import, the Energy Dashboard may need the next Home Assistant statistics cycle before history appears. If imported history does not show as expected, check Developer Tools -> Statistics for issues with `sensor.yorkshire_water_estimated_cumulative_usage`.

### Troubleshooting the import action

After copying a new `services.yaml` into Home Assistant, fully restart Home Assistant so the service metadata and integration code are loaded together.

The action appears in Developer Tools -> Actions as Yorkshire Water import statistics. If it does not appear, confirm the Yorkshire Water integration is loaded and restart Home Assistant rather than only reloading YAML.

For CSV imports, `file_path` must be readable from inside Home Assistant. For example, a file copied to the Home Assistant config share as `yorkshire_water/June 2026.csv` should be referenced as `/config/yorkshire_water/June 2026.csv`.

Home Assistant may already have created long-term statistics for the live cumulative sensor, so a CSV import can overlap existing statistics. Run a dry run first. If overlap is detected, review the reported requested and overlapping date ranges before using `allow_overwrite: true`.

If the Energy Dashboard shows negative water usage after an earlier bad import, the cumulative statistics stepped backwards. Remove or correct the affected long-term statistics for `sensor.yorkshire_water_estimated_cumulative_usage` in Developer Tools -> Statistics, or restore a recorder backup from before the import. Do not rerun an overwrite import until the dry run reports a non-zero aligned baseline and `negative_dashboard_deltas_avoided: true`.

`allow_overwrite: true` does not override monotonic safety. If existing future statistics are already corrupted or too low, the import may still refuse to run and return repair diagnostics. Start with `repair_mode: plan_only` to review the affected date range, prior statistic, overlapping statistics, future statistic, required baseline, and suggested repair strategy.

Repair modes are advanced and should be dry-run first. `repair_mode: ignore_future_anchor` is dry-run only and shows what the import would look like if an unsafe future anchor were ignored. `repair_mode: rebase_from_live` uses the current live cumulative sensor value as the anchor when that can create non-negative, internally monotonic rows. The safest recovery remains restoring a recorder backup from before the bad import.

## Cost Tracking

Cost sensors are separate from the Energy Dashboard water usage sensor. Home Assistant's Energy Dashboard should use the cumulative water sensor in m³, while the cost sensors are normal monetary sensors in GBP for Lovelace cards, reports, and dashboards.

Yorkshire Water currently provides clean water, sewerage, and total cost values in the captured daily and monthly/yearly usage payloads. The integration exposes period total cost sensors for yesterday, today, week to date, previous week, month to date, and year to date, with clean water and sewerage breakdowns retained as attributes where available.

These values are portal and tariff estimates. They may differ from final bill calculations after billing adjustments, tariff changes, rounding, or account-specific charges.

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Open the custom repositories dialog.
3. Add `https://github.com/Crash-Evans/ha_yorkshire_water` as an Integration repository.
4. Download Yorkshire Water.
5. Restart Home Assistant.
6. Go to Settings -> Devices & Services -> Add Integration.
7. Search for Yorkshire Water.

### Manual

Copy `custom_components/yorkshire_water` into your Home Assistant `custom_components` directory:

```text
config/
└── custom_components/
    └── yorkshire_water/
        ├── __init__.py
        ├── api.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── services.yaml
        ├── sensor.py
        ├── statistics_import.py
        └── strings.json
```

Restart Home Assistant, then add Yorkshire Water from Settings -> Devices & Services.

## Configuration

The supported setup starts with guided Yorkshire Water sign-in. Home Assistant opens the provider link in a new tab; after completing portal sign-in, paste the complete final callback URL into the flow. The callback is matched to the active, short-lived sign-in attempt and no password, authorization code, code verifier, token JSON, or browser developer tools are requested.

Existing beta installations can choose **Use a temporary access token (advanced)** when guided sign-in is unavailable. This fallback lasts only for the token's valid lifetime and returns to guided reauthentication when it expires. Working existing installations are not forced to migrate until their next required reauthentication.

Access tokens typically expire after about 900 seconds. Persistent unattended renewal is disabled until a redacted live evidence record proves that Yorkshire Water issues a refresh token and accepts renewal after access-token expiry. The exact evidence requirements are in [docs/auth_capability_evidence.md](docs/auth_capability_evidence.md). A provider rejection or temporary outage remains a guided recovery path; it is never presented as durable access.

The integration's diagnostic status entity reports `Connected — data current`, `Update delayed — retrying`, or `Sign-in required — data last updated <time>`, with a non-secret `last_successful_update` attribute. The integration entry itself uses Home Assistant's native Loaded, Setup retry, and Needs attention lifecycle states.

If you provide an account reference but not a meter reference, the integration tries to discover the meter reference from the smart meter meter-details endpoint. If you provide neither reference, the integration remains in endpoint discovery mode.

The integration stores only the access token, optional evidence-gated refresh token, safe expiry timestamp, and configured account or meter references in the Home Assistant config entry. It redacts secrets in integration logs. Do not paste access tokens, ID tokens, refresh tokens, authorization codes, code verifiers, full token responses, account references, meter references, cookies, screenshots, or raw portal captures into GitHub issues or logs.

## API Discovery Notes

Yorkshire Water beta support currently uses these captured smart meter endpoints with bearer-token auth:

- `GET /api/account/smartmeter/meter-details?accountReference=...`
- `GET /api/account/smartmeter/current-consumption?meterReference=...`
- `GET /api/account/smartmeter/your-usage?meterReference=...`

The API client has async request helpers, structured errors, safe redacted debug logging, and parser scaffolding for captured response schemas.

Sensitive values redacted from debug logs include authorization headers, cookies, tokens, customer references, account IDs, and meter IDs.

See [docs/api_discovery.md](docs/api_discovery.md) and [docs/redaction_checklist.md](docs/redaction_checklist.md) before sharing any captured request or response structure.

## Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.yorkshire_water: debug
```

Debug logs are designed to be useful during endpoint discovery while redacting sensitive fields.

## Validation

From the repository root:

```bash
python -m compileall custom_components/yorkshire_water
```

If your development environment has Home Assistant tooling installed, also run manifest validation and any configured linter or test suite.

## History

Historical changelog entries and license attribution are retained where appropriate, but user-facing integration branding is now Yorkshire Water.
