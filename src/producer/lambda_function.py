import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs = boto3.client('sqs')
queue_url = os.environ.get('QUEUE_URL')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda function to handle API Gateway requests and send messages to SQS
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        if 'body' in event:
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Invalid JSON in request body'
                    })
                }
        else:
            body = {}
        
        # Validate required fields
        if 'message' not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: message'
                })
            }
        
        # Create message payload
        message_payload = {
            'message': body['message'],
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': context.aws_request_id,
            'source': 'api-gateway'
        }
        
        # Add optional fields
        if 'priority' in body:
            message_payload['priority'] = body['priority']
        if 'category' in body:
            message_payload['category'] = body['category']
        
        # Send message to SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_payload),
            MessageAttributes={
                'RequestId': {
                    'StringValue': context.aws_request_id,
                    'DataType': 'String'
                },
                'Timestamp': {
                    'StringValue': message_payload['timestamp'],
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Message sent to SQS: {response['MessageId']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Message sent successfully',
                'message_id': response['MessageId'],
                'timestamp': message_payload['timestamp']
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        } 