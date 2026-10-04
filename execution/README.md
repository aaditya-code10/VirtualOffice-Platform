# Execution (Layer 3: Doing the work)

This directory contains deterministic Python scripts that perform the actual work: API calls, data transformations, database interactions, and file operations.

## Design Principles

1. **Deterministic & Testable**: Scripts take explicit arguments or read configuration from `.env`, do the work, and exit with status 0 on success or non-zero on failure.
2. **Commented & Understandable**: Code should be self-documenting and easy for both humans and AI agents to inspect, debug, and patch.
3. **Environment & Secrets**: Load secrets and environment variables from `.env` at the project root. Never hardcode credentials.
4. **Intermediate Files**: Save all temporary or scratch data to `.tmp/`. Never commit `.tmp/` files.
5. **Self-Annealing Ready**: When a script encounters an unexpected API change or error, the error message and traceback should clearly state what broke so the orchestrator can fix the script and update the directive.

## Running Execution Scripts

From the repository root:
```bash
python execution/<script_name>.py --arg value
```
