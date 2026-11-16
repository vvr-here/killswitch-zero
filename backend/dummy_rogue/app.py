import json
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simulated target workload function.
    In normal operation, processes a lightweight mock workload.
    When quarantined (concurrency clamped to 0), AWS Lambda immediately throttles
    all incoming requests with HTTP 429 (TooManyRequestsException).
    """
    logger.info(f"Target function invoked with event: {json.dumps(event)}")
    
    # Simulate standard microservice task (e.g. invoice calculation or image processing)
    processing_time_ms = int(event.get('simulate_work_ms', 50))
    time.sleep(processing_time_ms / 1000.0)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Workload processed successfully",
            "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'RogueTargetFunction'),
            "processed_at": time.time()
        })
    }
