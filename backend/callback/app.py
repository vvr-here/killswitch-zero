import json
import logging
import os
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn_client = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

INCIDENT_TABLE_NAME = os.environ.get('INCIDENT_TABLE')
incident_table = dynamodb.Table(INCIDENT_TABLE_NAME) if INCIDENT_TABLE_NAME else None

def handler(event, context):
    """
    Control Plane Callback Function (REST API: POST /action).
    Secured by API Key.
    Resumes the paused Step Function state machine by sending SendTaskSuccess.
    """
    logger.info(f"Callback invoked with event: {json.dumps(event)}")
    
    # 1. Parse payload
    body = {}
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        except Exception as e:
            logger.error(f"Failed to parse body: {e}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Invalid JSON body"})
            }

    incident_id = body.get('incident_id')
    action = body.get('action', 'RESTORE').upper()  # RESTORE or TERMINATE
    task_token = body.get('taskToken')
    
    if not incident_id and not task_token:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Either 'incident_id' or 'taskToken' is required"})
        }

    # 2. Lookup task token from DynamoDB if not supplied directly
    if not task_token and incident_table and incident_id:
        try:
            resp = incident_table.get_item(Key={'IncidentId': incident_id})
            item = resp.get('Item')
            if item:
                task_token = item.get('TaskToken')
            else:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": f"Incident {incident_id} not found"})
                }
        except ClientError as e:
            logger.error(f"Error querying DynamoDB: {e.response['Error']['Message']}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Database lookup failed"})
            }

    if not task_token:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "No active TaskToken found for this incident"})
        }

    # 3. Resume Step Function
    try:
        logger.info(f"Sending task success with action: {action}")
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps({
                "action": action,
                "authorized_at": datetime.now(timezone.utc).isoformat(),
                "actor": "Secured-Control-Plane-Admin"
            })
        )
    except ClientError as e:
        logger.error(f"Step Functions send_task_success failed: {e.response['Error']['Message']}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Failed to resume workflow: {e.response['Error']['Message']}"})
        }

    # 4. Update incident status in DynamoDB
    if incident_table and incident_id:
        new_status = "RESOLVED_TERMINATED" if action == "TERMINATE" else f"ACTION_DISPATCHED_{action}"
        try:
            incident_table.update_item(
                Key={'IncidentId': incident_id},
                UpdateExpression="SET #st = :status, HumanDecision = :action, DecisionTimestamp = :ts",
                ExpressionAttributeNames={'#st': 'Status'},
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':action': action,
                    ':ts': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Could not update incident state: {e}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "SUCCESS",
            "incident_id": incident_id,
            "action": action,
            "message": f"Circuit breaker resumed with action: {action}"
        })
    }
