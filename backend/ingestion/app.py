import json
import os
import re
import time
import uuid
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

VELOCITY_TABLE_NAME = os.environ.get('VELOCITY_TABLE')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
DEFAULT_ROGUE_FUNCTION = os.environ.get('ROGUE_FUNCTION_NAME', 'KillSwitch-RogueTargetFunction')
BURST_THRESHOLD = int(os.environ.get('BURST_THRESHOLD', '50'))

velocity_table = dynamodb.Table(VELOCITY_TABLE_NAME) if VELOCITY_TABLE_NAME else None

def handler(event, context):
    """
    Ingestion & Rate Tracking Function (Data Plane).
    Performs atomic increments on a minute-level tumbling window in DynamoDB.
    When invocation rate crosses the anomaly threshold, triggers Step Functions circuit breaker.
    """
    logger.info(f"Received telemetry event: {json.dumps(event)}")
    
    # 1. Parse payload
    body = {}
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        except Exception as e:
            logger.warning(f"Could not parse body as JSON: {e}")
            body = {}
            
    req_function = body.get('function_name')
    if not req_function or req_function in ['RogueTargetFunction', 'KillSwitch-RogueTargetFunction', 'default']:
        target_function = DEFAULT_ROGUE_FUNCTION
    else:
        target_function = req_function

    batch_invocations = int(body.get('invocations', 1))
    force_trigger = bool(body.get('force', False))
    
    now = datetime.now(timezone.utc)
    current_minute = now.strftime('%Y-%m-%dT%H:%M')
    epoch_now = int(time.time())
    ttl_expiry = epoch_now + (24 * 3600)  # 24-hour retention
    
    # 2. Atomic Tumbling Window Increment in DynamoDB
    current_count = batch_invocations
    if velocity_table:
        try:
            response = velocity_table.update_item(
                Key={
                    'FunctionName': target_function,
                    'Window_Minute': current_minute
                },
                UpdateExpression="ADD InvocationCount :val SET TTL_Expiry = if_not_exists(TTL_Expiry, :ttl)",
                ExpressionAttributeValues={
                    ':val': batch_invocations,
                    ':ttl': ttl_expiry
                },
                ReturnValues="UPDATED_NEW"
            )
            current_count = int(response['Attributes']['InvocationCount'])
            logger.info(f"Function {target_function} minute count: {current_count} (threshold: {BURST_THRESHOLD})")
        except ClientError as e:
            logger.error(f"Error updating tumbling counter: {e.response['Error']['Message']}")

    # 3. Anomaly Evaluation & Circuit Breaker Trigger
    circuit_breaker_triggered = False
    execution_arn = None
    
    # Trigger circuit breaker if threshold breached
    # Triggers on the breach crossover or when explicitly forced by simulation test
    is_breach_crossover = current_count >= BURST_THRESHOLD and (current_count - batch_invocations) < BURST_THRESHOLD
    if (is_breach_crossover or force_trigger) and current_count >= BURST_THRESHOLD:
        logger.warning(f"ANOMALY DETECTED: {target_function} rate {current_count} req/min exceeds threshold {BURST_THRESHOLD}")
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        if STATE_MACHINE_ARN:
            try:
                # Idempotent execution name conforming strictly to Step Functions naming rules ([a-zA-Z0-9-_])
                clean_target = re.sub(r'[^a-zA-Z0-9-_]', '-', target_function.split(':')[-1])[:20]
                clean_minute = current_minute.replace(':', '-').replace('T', '-')
                exec_name = f"KillSwitch-{clean_target}-{clean_minute}-{uuid.uuid4().hex[:4]}"
                
                sfn_payload = {
                    "incident_id": incident_id,
                    "target_function": target_function,
                    "burst_velocity": current_count,
                    "window_minute": current_minute,
                    "threshold": BURST_THRESHOLD,
                    "timestamp": now.isoformat()
                }
                
                sfn_resp = sfn_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=exec_name,
                    input=json.dumps(sfn_payload)
                )
                execution_arn = sfn_resp.get('executionArn')
                circuit_breaker_triggered = True
                logger.info(f"Triggered Step Functions execution: {execution_arn}")
            except ClientError as e:
                # If execution already running for this exact window, handle gracefully
                logger.warning(f"Step Functions start_execution warning: {e.response['Error']['Message']}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "RECORDED",
            "function_name": target_function,
            "window_minute": current_minute,
            "current_velocity": current_count,
            "threshold": BURST_THRESHOLD,
            "circuit_breaker_triggered": circuit_breaker_triggered,
            "execution_arn": execution_arn
        })
    }
