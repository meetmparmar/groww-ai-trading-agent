# Groww AI Trading Agent

Paper-trading MVP for Indian equities. Repository scaffold only; no application behavior or AWS resources are implemented yet.

## Layout

- `src/groww_agent/` — future Python application services.
- `tests/` — future unit, integration, recovery, and paper-isolation checks.
- `infra/terraform/` — future AWS infrastructure as code.
- `deploy/compose/` — future Docker Compose deployment configuration.
- `docs/` — architecture decisions and operations guidance.
- `docs/WORK-TRACKER.md` — authoritative requirements, decisions, and task tracker.

## Baseline

AWS Mumbai (`ap-south-1`), one Linux EC2 instance, Docker Compose, persistent storage, backups, monitoring, and tested recovery. No EKS/Kubernetes. Paper trading only. ₹50,000 default simulated capital; 0.5% planned risk per trade; 1.5% daily loss threshold; authenticated Telegram session approval.

## Current authorization

Repository scaffolding and private GitHub publication are authorized. All local repositories must remain within the current workspace. Do not infer authorization to implement application behavior, create AWS resources, subscribe to paid services, or execute trades. Resolve requirements and obtain the appropriate implementation instruction before proceeding. Provisioning requires separate authorization.

## Next step

Continue T01 in the master work document. This scaffold partially prepares T14 but does not complete its startup, configuration, and paper-mode acceptance criteria.

No dependency installation, application startup, or Terraform apply command is provided because those artifacts are not implemented. This repository is local; no remote repository has been created.
