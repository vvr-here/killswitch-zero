# KillSwitch Zero: Hackathon Submission Package & 3-Minute Video Script

> **Project Name:** KillSwitch Zero  
> **Tagline:** Autonomous Serverless Runaway Bill & Blast-Radius Circuit Breaker  
> **Category:** AWS Serverless Weekend Challenge (Scale-to-Zero)  
> **Tech Stack:** AWS Lambda, Amazon API Gateway (HTTP & REST), Amazon DynamoDB, AWS Step Functions (Standard), Amazon S3, Amazon CloudFront (OAC), AWS SAM

---

## 1. Project Submission Text (Copy & Paste Ready)

### The Problem We Picked
Every cloud builder has experienced the existential dread of a runaway recursive Lambda loop, a cascaded DynamoDB scan, or an unthrottled endpoint racking up a **$10,000 AWS bill overnight**. 

While AWS Budgets and CloudWatch Alarms exist, they have built-in metric aggregation delays of **1 to 5 minutes**. In a recursive loop executing 1,000 times per second, the financial damage is already done before an alert email even lands in your inbox. Developers need an autonomous, sub-second emergency circuit breaker that operates at the edge without adding servers or persistent background cost.

### What Our Build Does
**KillSwitch Zero** is a fully serverless, event-driven circuit breaker that monitors execution velocity in tumbling one-minute windows. When a rogue function breaches its safety threshold:
1. **Sub-Second Blast Radius Containment:** Invokes `lambda:PutFunctionConcurrency(ReservedConcurrentExecutions=0)`, instantly dropping incoming invocations with HTTP 429 (`TooManyRequestsException`) and freezing the financial leak in under 200ms.
2. **Standard Step Functions Orchestration:** Launches a durable state machine that generates an immutable forensic incident autopsy, uploads it to Amazon S3, and creates a universal **SigV4 24-hour Pre-signed URL**.
3. **Zero-Cost Human-in-the-Loop:** Pauses the workflow using `.waitForTaskToken` at zero idle cost. The admin receives a one-click link to the autopsy and can authorize a traffic restore or confirm permanent lockdown directly from the secured Command Center dashboard.
4. **Scale-to-Zero:** Zero servers, zero containers, and zero background polling. When idle, the monthly infrastructure cost is strictly **$0.00**.

### Serverless AWS Services & Architecture
* **Data Plane (Amazon API Gateway HTTP API):** Ingests high-throughput telemetry with open CORS.
* **Velocity Tracker (Amazon DynamoDB):** Atomic tumbling window counter (`ADD InvocationCount :val`) with a native **24-hour TTL** that auto-purges historical data without maintenance.
* **Orchestration (AWS Step Functions - Standard):** Coordinates quarantine, task token pauses, and remediation with comprehensive error `Catch` handlers.
* **Compute (AWS Lambda - Python 3.12):** Micro-functions running under strict least-privilege IAM policies.
* **Control Plane (Amazon API Gateway REST API):** Secured management endpoint requiring an `x-api-key` header to dispatch human decisions.
* **Edge & UI (Amazon CloudFront + Amazon S3):** Single-page Command Center frontend served securely via CloudFront with modern **Origin Access Control (OAC)** and forced HTTPS redirection.
* **Forensics (Amazon S3):** Stores JSON post-mortems with 24-hour pre-signed access links.

---

## 2. The 3-Minute Video Demo Script (Storyboard)

| Timestamp | Screen Display | Voiceover / Action Script |
| :--- | :--- | :--- |
| **0:00 - 0:35** | **Slide / Diagram:** Show the $10k runaway bill meme + Architecture diagram. | *"Every AWS engineer knows this nightmare: you write a recursive Lambda or an unconstrained queue consumer, and wake up to a $10,000 bill. CloudWatch Alarms take 5 minutes to trigger—way too late. We built **KillSwitch Zero**: an autonomous, sub-second serverless circuit breaker that clamps runaway execution storms in milliseconds and scales to absolute zero."* |
| **0:35 - 1:15** | **Browser:** KillSwitch Command Center dashboard showing green "OPERATIONAL" badge and 0 req/min chart. | *"Here is the KillSwitch Command Center, served from a private S3 bucket through CloudFront with Origin Access Control. Our target function is running normally. Now, let's trigger a simulated recursive loop storm of 100 requests into our HTTP API Data Plane."* <br/><br/>**(Action: Click 'TRIGGER RECURSIVE STORM')** |
| **1:15 - 1:50** | **Browser:** Chart spikes red $\rightarrow$ Big Red Alert Banner flashes: `EMERGENCY BLAST-RADIUS QUARANTINE ENGAGED`. | *"In less than 200 milliseconds, our DynamoDB atomic tumbling window counter caught the velocity spike. The Step Functions Standard state machine engaged, calling `PutFunctionConcurrency = 0`. The target function's concurrency is now locked to zero. All runaway loops are dead in their tracks, preventing an estimated $120/hr in runaway charges."* |
| **1:50 - 2:25** | **Browser:** Click `View S3 Pre-signed Autopsy Report ↗`. Opens raw JSON in new tab. Click `Authorize Traffic Restore`. | *"Step Functions compiled an immutable forensic autopsy into Amazon S3 and generated this 24-hour SigV4 Pre-signed URL. As the admin, I can inspect the exact timeline, anomaly factor, and financial blast radius. Step Functions is currently paused at zero compute cost using the `waitForTaskToken` pattern. When I click 'Authorize Traffic Restore', our secured REST API sends the task token back, and Step Functions lifts the concurrency clamp."* |
| **2:25 - 3:00** | **IDE / Terminal:** Show `template.yaml` and CloudFront/Step Functions console. | *"KillSwitch Zero uses AWS SAM for 1-command deployment, enforces strict least-privilege IAM policies, separates the open Data Plane from the API-Key secured Control Plane, and auto-cleans its database with DynamoDB TTL. No servers to babysit, zero idle cost. Just serverless doing what it does best."* |

---

## 3. How to Deploy in 3 Minutes

```bash
# 1. Build the SAM package
sam build

# 2. Deploy to your AWS account (interactive guided deployment)
sam deploy --guided

# 3. Upload the dashboard frontend to S3
aws s3 sync frontend/ s3://<DashboardBucketName>/

# 4. Open the CloudFront URL
# Open https://<DistributionDomainName> in your browser!
```
