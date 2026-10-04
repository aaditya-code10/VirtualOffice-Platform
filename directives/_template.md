# [SOP Title / Task Name]

## 1. Goal
Describe the objective of this task in plain language, explaining the desired outcome and business impact.

## 2. Inputs
- **Parameters / Arguments**: e.g., target entity ID, date range, search query
- **Required Credentials / Env**: e.g., API keys in `.env`
- **Source Files / Data**: e.g., raw CSVs, spreadsheets, database tables

## 3. Execution Tools
List the deterministic script(s) in `execution/` used by this directive:
- `execution/[tool_name].py`: Brief explanation of its responsibility, flags, and usage.

## 4. Outputs
- **Deliverables**: Cloud-accessible outputs (Google Sheets, Slides, reports, API endpoints).
- **Intermediates**: Local temporary files stored in `.tmp/` (e.g., `.tmp/raw_data_[id].json`).

## 5. Procedure
Step-by-step instructions for the Orchestrator:
1. **Prepare Inputs**: Validate arguments and verify environment variables in `.env`.
2. **Execute Scripts**: Run the deterministic Python script(s) from `execution/`.
3. **Handle Errors**: If a script exits with non-zero status, inspect the error output and follow the self-annealing loop.
4. **Publish Deliverables**: Transfer results to the designated deliverable medium.
5. **Clean Up**: Intermediate files in `.tmp/` can be retained for debugging or cleared.

## 6. Edge Cases & Annealing Notes
Record lessons learned, API constraints, and handling strategies:
- *API Rate Limits*: Document rate limits, exponential backoff, or batch endpoints.
- *Data Anomalies*: Document how missing fields, nulls, or schema shifts are handled.
