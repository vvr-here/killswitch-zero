import json
import logging
import os
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

INCIDENT_TABLE_NAME = os.environ.get('INCIDENT_TABLE')
incident_table = dynamodb.Table(INCIDENT_TABLE_NAME) if INCIDENT_TABLE_NAME else None

def handler(event, context):
    """
    Restore Function.
    Executed when the admin authorizes traffic restoration.
    Calls lambda:DeleteFunctionConcurrency to lift the 0-concurrency emergency brake.
    """
    logger.info(f"Restore invoked with event: {json.dumps(event)}")
    
    target_function = event.get('target_function')
    quarantine_result = event.get('quarantine_result', {}).get('Payload', {})
    incident_id = quarantine_result.get('incident_id') or event.get('incident_id', 'Unknown')
    
    if not target_function:
        raise ValueError("Missing 'target_function' in restore event payload")

    # 1. Lift Concurrency Brake via AWS Lambda SDK
    try:
        logger.info(f"Lifting concurrency lock on {target_function}")
        lambda_client.delete_function_concurrency(
            FunctionName=target_function
        )
        logger.info(f"Successfully deleted reserved concurrency for {target_function}")
    except ClientError as e:
        logger.error(f"Error restoring concurrency: {e.response['Error']['Message']}")
        raise e

    # 2. Update DynamoDB Incident Record
    now_iso = datetime.now(timezone.utc).isoformat()
    if incident_table and incident_id:
        try:
            incident_table.update_item(
                Key={'IncidentId': incident_id},
                UpdateExpression="""
                    SET #st = :status,
                        ResolvedAt = :ts,
                        RestorationStatus = :rst
                """,
                ExpressionAttributeNames={'#st': 'Status'},
                ExpressionAttributeValues={
                    ':status': 'RESOLVED_RESTORED',
                    ':ts': now_iso,
                    ':rst': 'CONCURRENCY_UNCLAMPED_STANDARD'
                }
            )
            logger.info(f"Incident {incident_id} marked as RESOLVED_RESTORED in DynamoDB")
        except ClientError as e:
            logger.warning(f"Could not update incident status in DynamoDB: {e}")

    return {
        "status": "RESOLVED_RESTORED",
        "incident_id": incident_id,
        "target_function": target_function,
        "restored_at": now_iso,
        "message": f"Successfully restored standard concurrency to {target_function}."
    }
