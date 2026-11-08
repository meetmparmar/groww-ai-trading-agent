# Project working rules

Read `docs/WORK-TRACKER.md` before starting work. It is the authoritative tracker; do not create a second task-status source.

- Maintain stable task IDs, evidence, decisions, and next-task status there.
- Work on one task at a time unless the owner changes that preference.
- Repository scaffolding is authorized. Application implementation and provisioning remain separately gated by owner instructions and unresolved requirements.
- Paper trading only. Do not add a live-order path or store live execution credentials.
- Do not run Terraform apply/destroy, create paid resources, or publish this repository without appropriate authorization.
- AWS baseline is Mumbai EC2 + Docker Compose, with no Kubernetes/EKS.
- Never commit credentials, state, plans, portfolio databases, or personal trading data.
- Missing limits, stale data, missing approval, and uncertain state must fail closed in future implementation.
- Verify current official documentation before selecting dependencies, provider versions, API capabilities, or cloud prices.
