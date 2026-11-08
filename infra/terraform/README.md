# AWS infrastructure as code

Terraform scaffolding only. The `.tf` files intentionally contain no provider configuration or resource definitions. They cannot provision the proposed architecture.

Target design: AWS Mumbai (`ap-south-1`), Linux EC2 + Docker Compose, persistent EBS, protected S3 backups, least-privilege IAM, CloudWatch, external heartbeat, and cost alerts. No EKS/Kubernetes. Instance sizing, networking, security groups, secrets, scheduling, backup policy, and state backend require design review.

Before implementation, verify current Terraform/AWS provider versions and official documentation, select/pin compatible versions, and decide remote-state access, encryption, locking, and bootstrap ownership. Commit the generated provider dependency lock file after review; never commit state, plans, or real variable files.

Before provisioning, complete T44 and T45: review current costs, capacity, availability tradeoffs, and obtain explicit provisioning authorization. Do not use `apply` or `destroy` for scaffold validation.
