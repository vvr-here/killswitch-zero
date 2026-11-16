# KillSwitch Zero ⚡
> Autonomous Serverless Circuit Breaker for Runaway Lambda Loops (Scale-to-Zero)

[![AWS SAM](https://img.shields.io/badge/AWS-SAM-orange?logo=amazon-aws&style=flat-square)](https://aws.amazon.com/serverless/sam/)
[![Step Functions](https://img.shields.io/badge/Step%20Functions-Standard-purple?logo=amazonaws&style=flat-square)](https://aws.amazon.com/step-functions/)
[![DynamoDB](https://img.shields.io/badge/DynamoDB-On--Demand-blue?logo=amazondynamodb&style=flat-square)](https://aws.amazon.com/dynamodb/)
[![Lambda](https://img.shields.io/badge/Lambda-Python%203.12-ffd43b?logo=awslambda&style=flat-square)](https://aws.amazon.com/lambda/)
[![Idle Cost](https://img.shields.io/badge/Idle%20Cost-%240.00%2Fmo-emerald?style=flat-square)](https://aws.amazon.com/serverless/)
[![License](https://img.shields.io/badge/License-MIT-white?style=flat-square)](LICENSE)

---

## ⚡ Overview
CloudWatch alarms take **1 to 5 minutes** to evaluate—far too slow to stop a recursive Lambda loop running at 1,000 req/sec from causing a catastrophic AWS bill.

**KillSwitch Zero** stops runaway loops in **<200 milliseconds** with **$0.00 idle cost**:
* **Sub-Second Emergency Brake:** Monitors 60s tumbling windows in DynamoDB. On breach, clamps target concurrency to `0` (`PutFunctionConcurrency = 0`). Rogue traffic immediately drops with HTTP 429.
* **Forensic S3 Autopsy:** Step Functions compiles an incident post-mortem into S3 with a 24-hour **SigV4 Pre-signed URL**.
* **Zero-Cost Human-in-the-Loop:** Pauses on `waitForTaskToken` at $0 compute cost until an admin authorizes traffic restoration or confirms permanent lockdown.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    classDef client fill:#1E293B,stroke:#475569,stroke-width:1px,color:#F8FAFC;
    classDef dataPlane fill:#0C4A6E,stroke:#0284C7,stroke-width:1.5px,color:#F0F9FF;
    classDef storage fill:#78350F,stroke:#D97706,stroke-width:1.5px,color:#FFFBEB;
    classDef sfn fill:#4C1D95,stroke:#8B5CF6,stroke-width:1.5px,color:#F5F3FF;
    classDef control fill:#064E3B,stroke:#059669,stroke-width:1.5px,color:#ECFDF5;

    subgraph DATA_PLANE["1. Data Plane & Detection"]
        Client["Workload Telemetry"]:::client -->|"POST /telemetry"| HttpApi["HTTP API Gateway"]:::dataPlane
        HttpApi --> IngestFn["Ingestion Lambda"]:::dataPlane
        IngestFn -->|"Atomic ADD :val"| DDB_Vel[("DynamoDB Velocity Table<br/>(24h TTL)")]:::storage
        IngestFn -->|"Rate > 50 req/min"| SFN["Step Functions Standard"]:::sfn
    end

    subgraph CONTAINMENT["2. Autonomous Containment & Autopsy"]
        SFN --> QFn["Quarantine Lambda<br/>(PutFunctionConcurrency = 0)"]:::sfn
        QFn --> NotifyFn["Notify & Presign Lambda"]:::sfn
        NotifyFn -->|"Archive Autopsy"| S3_Autopsy[("S3 Forensics Bucket<br/>(SigV4 Link)")]:::storage
        NotifyFn --> WaitToken["State Machine Paused<br/>(waitForTaskToken)"]:::sfn
    end

    subgraph CONTROL_PLANE["3. Control Plane & Remediation"]
        Admin["Admin / Dashboard"]:::client -->|"POST /action (x-api-key)"| RestApi["REST API Gateway"]:::control
        RestApi --> CallbackFn["Callback Lambda"]:::control
        CallbackFn -->|"SendTaskSuccess"| WaitToken
        WaitToken --> RestoreFn["Restore Lambda<br/>(DeleteFunctionConcurrency)"]:::sfn
        RestoreFn --> DDB_Inc[("DynamoDB Incident Table")]:::storage
    end
```

---

## 📊 Resources & Scale-to-Zero Cost Model

| Service | Component | Role | Idle Cost |
| :--- | :--- | :--- | :---: |
| **API Gateway** | HTTP API | High-throughput open telemetry ingestion (`POST /telemetry`) | **$0.00** |
| **DynamoDB** | `VelocityTable` | Atomic 60s tumbling counter with 24h native TTL auto-purge | **$0.00** |
| **Step Functions** | Standard State Machine | Orchestrates quarantine and zero-cost `waitForTaskToken` pause | **$0.00** |
| **AWS Lambda** | 7 Micro-Functions | Python 3.12 under strict least-privilege scoped IAM roles | **$0.00** |
| **API Gateway** | REST API | Secured control plane requiring `x-api-key` (`POST /action`, `GET /status`) | **$0.00** |
| **CloudFront & S3** | OAC Distribution + Bucket | Private static hosting for the Geist Sans Command Center UI | **$0.00** |
| **S3** | `ForensicBucket` | WORM-compliant JSON autopsies with 24h SigV4 pre-signed links | **$0.00** |

---

## 🚀 Deployment (3 Minutes)

### Option A: Via AWS Console (CloudShell)
*No IAM user or local CLI installation required.*

1. Open **AWS CloudShell** in your target region (e.g., **`ap-southeast-2`** or **`us-east-1`**).
2. Upload this repo zipped (`skill-builder.zip`) and run:
   ```bash
   unzip skill-builder.zip && cd skill-builder
   sam build
   sam deploy --guided
   aws s3 sync frontend/ s3://<DashboardBucketName>/
   ```

### Option B: Via Local Terminal
```bash
sam build
sam deploy --guided
aws s3 sync frontend/ s3://<DashboardBucketName>/
```

---

## ⚡ Demo & Verification

### 1. Instant Offline Sandbox Mode
Double-click `frontend/index.html` in your browser:
* Click **Baseline Telemetry (5 req)**: Observe normal green baseline.
* Click **Trigger Recursive Storm (100 req)**: Concurrency clamps to `0 (LOCKED)`, ambient spotlight halo turns red, and the forensic autopsy modal unlocks.
* Click **Authorize Restore**: Circuit breaker resets to `STANDBY`.

### 2. Live Telemetry CLI Test
```bash
python scripts/simulate_burst.py <HttpIngestApiUrl> 100
```

---

## 📁 Project Structure

```text
skill-builder/
├── template.yaml                  # Master SAM IaC (17 Serverless resources)
├── backend/                       # Python 3.12 Lambda microservices
│   ├── ingestion/                 # Tumbling window atomic counter & trigger
│   ├── quarantine/                # Concurrency clamp (PutFunctionConcurrency=0)
│   ├── notify_presign/            # S3 autopsy JSON writer & SigV4 signer
│   ├── callback/                  # TaskToken resume dispatcher (x-api-key)
│   ├── restore/                   # Concurrency brake release
│   ├── status/                    # Real-time state inspector
│   └── dummy_rogue/               # Simulated workload target
├── orchestration/
│   └── killswitch.asl.json        # Step Functions ASL with waitForTaskToken
├── frontend/
│   └── index.html                 # Linear Charcoal Command Center (Zero-build)
├── scripts/
│   └── simulate_burst.py          # Synthetic loop storm simulator
└── docs/
    ├── ARCHITECTURE.md            # In-depth architectural & IAM specifications
    └── SUBMISSION_PACKAGE.md      # Hackathon submission package & video script
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
