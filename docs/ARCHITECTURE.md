# KillSwitch Zero: System Architecture Specification

> **Project Name:** KillSwitch Zero  
> **Classification:** Cloud Circuit Breaker & Autonomous Blast-Radius Containment  
> **Core Objective:** Millisecond-level mitigation of runaway Lambda loops and recursive execution storms, scaling to absolute zero ($0.00 idle cost).

---

## 1. End-to-End System Architecture Diagram

```mermaid
flowchart TD
    %% Styling
    classDef client fill:#1E293B,stroke:#475569,stroke-width:1px,color:#F8FAFC;
    classDef dataPlane fill:#0C4A6E,stroke:#0284C7,stroke-width:1.5px,color:#F0F9FF;
    classDef storage fill:#78350F,stroke:#D97706,stroke-width:1.5px,color:#FFFBEB;
    classDef sfn fill:#4C1D95,stroke:#8B5CF6,stroke-width:1.5px,color:#F5F3FF;
    classDef control fill:#064E3B,stroke:#059669,stroke-width:1.5px,color:#ECFDF5;
    classDef forensic fill:#831843,stroke:#DB2777,stroke-width:1.5px,color:#FDF2F8;

    subgraph INGESTION["1. High-Speed Data Plane"]
        Client["Rogue / Monitored Workload"]:::client -->|"POST /telemetry<br/>(Sub-ms Open CORS)"| HttpApi["Amazon API Gateway<br/>(HTTP API)"]:::dataPlane
        HttpApi --> IngestFn["Ingestion Lambda<br/>(Velocity Evaluator)"]:::dataPlane
    end

    subgraph DETECTION["2. Storage & Tumbling Window Counter"]
        IngestFn -->|"Atomic ADD :val<br/>(60s Tumbling Window)"| DDB_Vel[("Amazon DynamoDB<br/>VelocityTable<br/>(TTL: 24h)")]:::storage
        IngestFn -->|"Rate > 50 req/min<br/>(Breach Trigger)"| SfnExec["StartExecution"]:::sfn
    end

    subgraph CONTAINMENT["3. Standard Orchestration (Step Functions)"]
        SfnExec --> SFN["Step Functions State Machine<br/>(Type: STANDARD)"]:::sfn
        SFN --> QFn["Quarantine Lambda<br/>(lambda:PutFunctionConcurrency = 0)"]:::sfn
        QFn --> NotifyFn["Notify & Presign Lambda<br/>(Injects $$.Task.Token)"]:::sfn
        NotifyFn -->|"Archive Autopsy"| S3_Forensic[("Amazon S3<br/>Forensics Bucket<br/>(SigV4 24h Link)")]:::forensic
        NotifyFn --> WaitToken["Pause State<br/>(.waitForTaskToken)"]:::sfn
    end

    subgraph CONTROL["4. Secured Control Plane & Dashboard"]
        Admin["Admin / Browser UI"]:::client -->|"HTTPS Only (OAC)"| CF["Amazon CloudFront"]:::control
        CF --> S3_Web[("Amazon S3<br/>Private Dashboard Bucket")]:::control
        Admin -->|"Inspect 1-Click Autopsy"| S3_Forensic
        Admin -->|"Authorize Decision<br/>(REST POST /action with x-api-key)"| RestApi["Amazon API Gateway<br/>(REST API - Secured)"]:::control
        RestApi --> CallbackFn["Callback Lambda"]:::control
        CallbackFn -->|"sfn:SendTaskSuccess(TaskToken)"| WaitToken
    end

    subgraph REMEDIATION["5. Remediation & Closure"]
        WaitToken --> Choice{"Human Decision"}:::sfn
        Choice -->|"RESTORE"| RestoreFn["Restore Lambda<br/>(lambda:DeleteFunctionConcurrency)"]:::sfn
        Choice -->|"TERMINATE"| Lockdown["Lockdown State<br/>(Keep Quarantined)"]:::sfn
        RestoreFn --> DDB_Inc[("Amazon DynamoDB<br/>IncidentTable")]:::storage
        Lockdown --> DDB_Inc
    end

    %% Error Handling Catch Paths
    QFn -.->|"Catch Error"| ErrState["HandleStateFailure<br/>(Log Error to DynamoDB)"]:::sfn
    NotifyFn -.->|"Catch Error"| ErrState
    RestoreFn -.->|"Catch Error"| ErrState
```

---

## 2. Component Specifications & Boundaries

| Component | AWS Resource | Role & Configuration | Security Posture |
| :--- | :--- | :--- | :--- |
| **Data Plane API** | `AWS::Serverless::HttpApi` | Ultra-low latency endpoint (`POST /telemetry`) ingesting synthetic workload metrics. | Open CORS (`*`) for simulation flexibility. |
| **Ingestion Engine** | `AWS::Serverless::Function` | Python 3.12. Atomic `UpdateItem` on DynamoDB tumbling window. Triggers Step Functions on breach. | Scoped to `dynamodb:UpdateItem` and `states:StartExecution`. |
| **Tumbling Counter** | `AWS::DynamoDB::Table` | PK: `FunctionName`, SK: `Window_Minute`. Atomic counter with **24-hour native TTL** auto-purge. | On-Demand billing (`PAY_PER_REQUEST`). $0 idle cost. |
| **State Machine** | `AWS::Serverless::StateMachine` | `Type: STANDARD`. Orchestrates emergency brake, `.waitForTaskToken`, and branch execution. | Native `Catch` blocks on all task states preventing hang-ups. |
| **Emergency Brake** | `AWS::Serverless::Function` | Calls `lambda:PutFunctionConcurrency(Reserved=0)` to freeze rogue function in <200ms. | Inline IAM policy scoped strictly to target function ARN. |
| **Autopsy Generator** | `AWS::Serverless::Function` | Writes JSON post-mortem to S3; generates 24-hour **SigV4 Pre-signed URL**. | Scoped to `s3:PutObject` on forensic bucket. |
| **Control Plane API** | `AWS::Serverless::Api` | REST API handling `POST /action` and `GET /status`. | **Enforced API Key (`x-api-key`)** to block unauthorized resume. |
| **Static Edge UI** | `AWS::CloudFront::Distribution` | Global CDN fronting private S3 bucket with **Origin Access Control (OAC)**. | Forced HTTPS (`redirect-to-https`). No public S3 access. |

---

## 3. The 5-Step Lifecycle of a Quarantine

1. **Normal Flow:** Monitored Lambda processes jobs; background telemetry emits counts to `POST /telemetry`. DynamoDB counts sit well below 50 req/min.
2. **Breach Event:** A recursive loop or runaway queue consumer bursts 100+ requests. The tumbling window counter atomically crosses the 50 req/min threshold.
3. **Sub-Second Containment:** Ingestion Lambda fires Step Functions $\rightarrow$ Quarantine Lambda calls `PutFunctionConcurrency(Reserved=0)`. All subsequent invocations immediately fail with HTTP 429.
4. **Human-in-the-Loop:** Step Functions writes the autopsy to S3, generates a SigV4 pre-signed URL, and pauses on `.waitForTaskToken` at **$0 compute cost**.
5. **Resolution:** Admin reviews the autopsy in the dashboard and clicks "Authorize Restore" $\rightarrow$ Control Plane calls `SendTaskSuccess` $\rightarrow$ Step Functions unclamps concurrency via `DeleteFunctionConcurrency`.
