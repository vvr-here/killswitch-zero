import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

INCIDENT_TABLE_NAME = os.environ.get('INCIDENT_TABLE')
VELOCITY_TABLE_NAME = os.environ.get('VELOCITY_TABLE')
ROGUE_FUNCTION_NAME = os.environ.get('ROGUE_FUNCTION_NAME', 'RogueTargetFunction')

incident_table = dynamodb.Table(INCIDENT_TABLE_NAME) if INCIDENT_TABLE_NAME else None
velocity_table = dynamodb.Table(VELOCITY_TABLE_NAME) if VELOCITY_TABLE_NAME else None

def handler(event, context):
    """
    Status Query Function (Control Plane: GET /status).
    Returns real-time concurrency status, active incidents, and tumbling window velocity.
    """
    logger.info("Fetching real-time circuit breaker status")
    
    # 1. Check Target Lambda Concurrency
    concurrency_status = "UNCONSTRAINED"
    reserved_concurrency = None
    try:
        resp = lambda_client.get_function_concurrency(FunctionName=ROGUE_FUNCTION_NAME)
        if 'ReservedConcurrentExecutions' in resp and resp['ReservedConcurrentExecutions'] is not None:
            reserved_concurrency = resp['ReservedConcurrentExecutions']
            if reserved_concurrency == 0:
                concurrency_status = "QUARANTINED_LOCKED_ZERO"
            else:
                concurrency_status = f"CUSTOM_LIMIT_{reserved_concurrency}"
        else:
            concurrency_status = "STANDARD_UNLIMITED"
    except ClientError as e:
        # If no reserved concurrency is configured, it raises ResourceNotFound or similar depending on API
        logger.info(f"Concurrency check note: {e.response['Error']['Message']}")
        concurrency_status = "STANDARD_UNLIMITED"

    # 2. Fetch Recent Incidents
    incidents = []
    if incident_table:
        try:
            resp = incident_table.scan(Limit=10)
            incidents = resp.get('Items', [])
            # Sort newest first
            incidents.sort(key=lambda x: x.get('QuarantineTimestamp', ''), reverse=True)
        except Exception as e:
            logger.warning(f"Could not read incidents: {e}")

    # 3. Fetch Recent Velocity Window Records
    velocity_records = []
    if velocity_table:
        try:
            resp = velocity_table.scan(Limit=15)
            velocity_records = resp.get('Items', [])
            velocity_records.sort(key=lambda x: x.get('Window_Minute', ''), reverse=True)
        except Exception as e:
            logger.warning(f"Could not read velocity: {e}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "target_function": ROGUE_FUNCTION_NAME,
            "concurrency_state": concurrency_status,
            "reserved_concurrency": reserved_concurrency,
            "active_incidents": incidents,
            "velocity_history": velocity_records
        }, default=str)
    }
