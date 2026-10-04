# Directives (Layer 1: What to do)

Directives are Standard Operating Procedures (SOPs) written in Markdown. They define the intent, requirements, and business logic for tasks.

## Anatomy of a Directive

Every directive in this directory should follow a consistent structure (see `_template.md`):

1. **Goal**: High-level objective and expected business value.
2. **Inputs**: Required parameters, data formats, credentials, or initial files.
3. **Execution Tools**: Which deterministic Python scripts in `execution/` should be invoked.
4. **Outputs**:
   - **Deliverables**: Final user-facing outputs (e.g., Google Sheets, Google Slides, cloud reports, production DB commits).
   - **Intermediates**: Temporary files stored in `.tmp/` during processing (never committed).
5. **Procedure**: Step-by-step instructions for the Orchestrator (the AI Agent) to follow.
6. **Edge Cases & Failure Recovery**: Known failure modes, retry rules, API limits, and self-annealing lessons.

## Operating Rules for Directives

- **Living documents**: Update directives when APIs change, edge cases are discovered, or performance optimizations are found.
- **Do not delete or overwrite without asking**: Directives represent accumulated institutional knowledge.
- **Keep directives high-level**: Directives describe *what* to do and *which tools* to run; deterministic code belongs in `execution/`.
