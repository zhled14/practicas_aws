# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Practice project for an AWS/Linux/IT infrastructure technical interview. It is a small Flask app used as a live demo of AWS concepts (ALB, ASG, EC2, IAM, S3) rather than a production service. The README (in Spanish) contains a day-by-day study/deployment plan and interview talking points — read it for the intended AWS architecture and timeline context before making structural changes.

Code comments and docs in this repo are written in Spanish; match that when editing existing files.

## Running locally

```bash
docker build -t infra-monitor .
docker run -p 8080:8080 infra-monitor
```

Or without Docker:
```bash
pip install -r requirements.txt
python app.py
```

App listens on `0.0.0.0:8080`.

Health check script: `./scripts/healthcheck.sh [host] [port]` (defaults to `localhost 8080`) — curls `/health` and exits non-zero on failure.

There is no test suite, linter, or build step configured in this repo.

## Environment variables

- `S3_BUCKET` — optional. If unset, `/report` computes results but skips the S3 upload.
- `AWS_REGION` — optional, defaults to `us-east-1`.

boto3 is expected to pick up credentials from the EC2 instance's IAM role (no hardcoded credentials — see the least-privilege `s3:PutObject` policy in README.md).

## Architecture

Single-file Flask app (`app.py`) with three routes:

- `/` — renders instance identity info. Calls `get_ec2_metadata()`, which uses IMDSv2 (token-based EC2 metadata service at `169.254.169.254`) to fetch `instance-id` and availability-zone. Falls back to `local-<hostname>` / `local-dev` when the metadata service isn't reachable (e.g., running locally or in Docker off-EC2) — this fallback is intentional and is what makes local/Docker runs work without EC2.
- `/health` — static 200 JSON, used as the ALB Target Group health check target.
- `/report` — reads `data/sample_test_logs.csv` with pandas, computes pass rate and top 5 failure causes (`causa_falla` column, grouped via `value_counts()`), and — if `S3_BUCKET` is set — uploads the JSON summary to `s3://$S3_BUCKET/reportes/tpy_report_<UTC timestamp>.json` via boto3. S3 upload failures are caught and reported in the response body (`s3_error`) rather than raising, so `/report` always returns a summary even if the upload fails.

This `/report` logic mirrors a TPY (test-pass-yield) failure analysis workflow; the CSV schema is `sn,estacion,resultado,causa_falla` where `resultado` is `PASS`/`FAIL`.

## Deployment model (see README.md for full detail)

`scripts/user_data.sh` is EC2 Launch Template user-data: installs Docker, clones this repo, builds the image, and runs it on port 80 with `S3_BUCKET`/`AWS_REGION` env vars baked in. It has two placeholders that must be filled in before use: `<TU_REPO_GIT>` (git repo URL) and `<NOMBRE_BUCKET>` (S3 bucket name). It supports both yum-based (Amazon Linux) and apt-based hosts.

Target infrastructure (not present as IaC in this repo — provisioned manually per the README plan): ALB across 2 public subnets/AZs → Target Group (health check `/health`) → Auto Scaling Group (min 2, desired 2, max 4) of EC2 instances running this container, each with an IAM role scoped to `s3:PutObject` on one bucket's `reportes/*` prefix.
