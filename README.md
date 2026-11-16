# KillSwitch Zero
> Autonomous Serverless Circuit Breaker for Runaway Lambda Loops (Scale-to-Zero)

[![AWS SAM](https://img.shields.io/badge/AWS-SAM-orange?logo=amazon-aws&style=flat-square)](https://aws.amazon.com/serverless/sam/)
[![Step Functions](https://img.shields.io/badge/Step%20Functions-Standard-purple?logo=amazonaws&style=flat-square)](https://aws.amazon.com/step-functions/)
[![DynamoDB](https://img.shields.io/badge/DynamoDB-On--Demand-blue?logo=amazondynamodb&style=flat-square)](https://aws.amazon.com/dynamodb/)
[![Lambda](https://img.shields.io/badge/Lambda-Python%203.12-ffd43b?logo=awslambda&style=flat-square)](https://aws.amazon.com/lambda/)
[![Idle Cost](https://img.shields.io/badge/Idle%20Cost-%240.00%2Fmo-emerald?style=flat-square)](https://aws.amazon.com/serverless/)
[![License](https://img.shields.io/badge/License-MIT-white?style=flat-square)](LICENSE)

---

## ⚡ Overview

CloudWatch alarms take **1–5 minutes** to evaluate—too slow to stop a recursive loop executing 1,000 req/sec from causing a catastrophic bill.

**KillSwitch Zero** clamps runaway workloads in **<200ms** at **$0.00 idle cost**:
* **Sub-Second Containment:** Tracks velocity in atomic 60s DynamoDB windows. On breach (>50 req/min), sets concurrency to `0` (`PutFunctionConcurrency = 0`), immediately dropping traffic with HTTP 429.
* **Forensic S3 Autopsy:** Step Functions compiles an immutable post-mortem with a 24-hour **SigV4 Pre-signed URL**.
* **Zero-Cost Recovery:** Pauses on `waitForTaskToken` at $0 compute cost until an admin authorizes restoration or permanent lockdown from the dashboard.

---

## 🏗️ Architecture

<p align="center">
  <img src="docs/mermaid-diagram.svg" alt="KillSwitch Zero Architecture Diagram" width="800">
</p>

---

## 📊 Resources & Costs

| Service | Component | Role | Idle Cost |
| :--- | :--- | :--- | :---: |
| **API Gateway** | HTTP API | Open telemetry ingestion (`POST /telemetry`) | **$0.00** |
| **DynamoDB** | `VelocityTable` | 60s tumbling counter with 24h native TTL auto-purge | **$0.00** |
| **Step Functions** | Standard State Machine | Workflow orchestration with zero-cost `waitForTaskToken` pause | **$0.00** |
| **AWS Lambda** | 7 Micro-Functions | Python 3.12 under least-privilege scoped IAM roles | **$0.00** |
| **API Gateway** | REST API | Control plane requiring `x-api-key` (`POST /action`, `GET /status`) | **$0.00** |
| **CloudFront & S3** | OAC Distribution + Bucket | Private hosting for the Command Center dashboard | **$0.00** |
| **S3** | `ForensicBucket` | Incident autopsies with 24h SigV4 pre-signed links | **$0.00** |

---

## 🚀 Deployment (3 Minutes)

Run via **AWS CloudShell** *(Console)* or **Local Terminal**:

```bash
# 1. Build and deploy backend stack
sam build
sam deploy --guided

# 2. Sync frontend dashboard to S3
aws s3 sync frontend/ s3://<DashboardBucketName>/
```

---

## ⚡ Demo & Verification

1. **Browser Sandbox:** Double-click `frontend/index.html`. Click **Trigger Recursive Storm (100 req)** to simulate a breach, lock concurrency to `0`, inspect the autopsy, and restore traffic.
2. **Live Telemetry CLI Test:**
   ```bash
   python scripts/simulate_burst.py <HttpIngestApiUrl> 100
   ```

---

## 📁 Project Structure

```text
killswitch-zero/
├── template.yaml                  # AWS SAM IaC (17 serverless resources)
├── LICENSE                        # MIT License
├── README.md
│
├── backend/                       # Python 3.13 Lambda microservices
│   ├── ingestion/                 # Tumbling window counter & anomaly trigger
│   ├── quarantine/                # Concurrency clamp (PutFunctionConcurrency=0)
│   ├── notify_presign/            # S3 autopsy generator & SigV4 signer
│   ├── callback/                  # TaskToken resume dispatcher (x-api-key)
│   ├── restore/                   # Concurrency brake release
│   ├── status/                    # Real-time state inspector
│   └── dummy_rogue/               # Simulated workload target
│
├── orchestration/
│   └── killswitch.asl.json        # Step Functions ASL with task tokens
│
├── frontend/
│   └── index.html                 # Linear Charcoal Command Center (Zero-build SPA)
│
├── scripts/
│   └── simulate_burst.py          # Synthetic storm CLI simulator
│
└── docs/
    ├── ARCHITECTURE.md            # Detailed architectural & IAM specifications
    ├── SUBMISSION_PACKAGE.md      # Hackathon submission write-up & video script
    └── mermaid-diagram.svg        # Architecture diagram vector asset
```

---

## 🧹 Teardown

```bash
aws s3 rm s3://<DashboardBucketName> --recursive
aws s3 rm s3://<ForensicBucketName> --recursive
sam delete --stack-name killswitch-zero
```

---

## 📄 License

[MIT](LICENSE)
