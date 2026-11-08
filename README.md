# Groww AI Trading Agent

Paper-trading MVP for Indian equities. The initial instrument-universe domain model is implemented; there is no trading runtime or AWS deployment.

## Layout

- `src/groww_agent/` — future Python application services.
- `tests/` — future unit, integration, recovery, and paper-isolation checks.
- `infra/terraform/` — future AWS infrastructure as code.
- `deploy/compose/` — future Docker Compose deployment configuration.
- `docs/` — architecture decisions and operations guidance.
- `docs/WORK-TRACKER.md` — authoritative requirements, decisions, and task tracker.

## Local development

Requires Python 3.10 or later. From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The virtual environment is local and ignored by Git. If Python was just installed while VS Code was open, restart VS Code so it picks up the updated user `PATH`. Alternatively, activate `.venv` with `.\.venv\Scripts\Activate.ps1` and use `python`.

## Baseline

AWS Mumbai (`ap-south-1`), one Linux EC2 instance, Docker Compose, persistent storage, backups, monitoring, and tested recovery. No EKS/Kubernetes. Paper trading only. ₹50,000 default simulated capital; 0.5% planned risk per trade; 1.5% daily loss threshold; authenticated Telegram session approval.

## Current authorization

Repository scaffolding and private GitHub publication are authorized. All local repositories must remain within the current workspace. Do not infer authorization to implement application behavior, create AWS resources, subscribe to paid services, or execute trades. Resolve requirements and obtain the appropriate implementation instruction before proceeding. Provisioning requires separate authorization.

## Next step

Continue with T02 in the master work document. T01's accepted scope is all currently listed cash-equity stocks on both NSE and BSE for intraday and swing paper trading. The exchange listing catalog is not yet loaded; T09 must verify a permitted source and T18 must implement ingestion before scanning can cover all stocks. The repository foundation does not complete T14's startup, configuration, and paper-mode acceptance criteria.

No trading application startup or Terraform apply command is provided because those artifacts are not implemented. This repository is local; no remote repository has been created.
