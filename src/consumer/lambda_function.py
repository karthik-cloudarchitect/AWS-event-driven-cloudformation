import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sns = boto3.client('sns')
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda function to process SQS messages and publish to SNS
    
    Args:
        event: SQS event containing messages
        context: Lambda context
        
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing {len(event['Records'])} messages from SQS")
        
        processed_messages = []
        failed_messages = []
        
        for record in event['Records']:
            try:
                # Parse SQS message
                message_body = json.loads(record['body'])
                message_id = record['messageId']
                
                logger.info(f"Processing message {message_id}: {message_body}")
                
                # Process the message
                processed_message = process_message(message_body, message_id)
                
                # Publish to SNS
                sns_response = publish_to_sns(processed_message, message_id)
                
                processed_messages.append({
                    'message_id': message_id,
                    'sns_message_id': sns_response['MessageId'],
                    'status': 'success'
                })
                
                logger.info(f"Successfully processed message {message_id}")
                
            except Exception as e:
                logger.error(f"Error processing message {record.get('messageId', 'unknown')}: {str(e)}")
                failed_messages.append({
                    'message_id': record.get('messageId', 'unknown'),
                    'error': str(e),
                    'status': 'failed'
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed_count': len(processed_messages),
                'failed_count': len(failed_messages),
                'processed_messages': processed_messages,
                'failed_messages': failed_messages
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise e

def process_message(message_body: Dict[str, Any], message_id: str) -> Dict[str, Any]:
    """
    Process the message and add metadata
    
    Args:
        message_body: Original message body
        message_id: SQS message ID
        
    Returns:
        Processed message with additional metadata
    """
    processed_message = {
        'original_message': message_body,
        'processed_at': datetime.utcnow().isoformat(),
        'message_id': message_id,
        'processor': 'consumer-lambda',
        'version': '1.0'
    }
    
    # Add processing metadata
    if 'priority' in message_body:
        processed_message['priority_level'] = message_body['priority']
    
    if 'category' in message_body:
        processed_message['category'] = message_body['category']
    
    # Add processing status
    processed_message['processing_status'] = 'completed'
    
    return processed_message

def publish_to_sns(message: Dict[str, Any], message_id: str) -> Dict[str, Any]:
    """
    Publish processed message to SNS topic
    
    Args:
        message: Processed message to publish
        message_id: Original message ID for tracking
        
    Returns:
        SNS publish response
    """
    try:
        # Create SNS message
        sns_message = {
            'default': json.dumps(message),
            'email': f"Message processed: {message.get('original_message', {}).get('message', 'No message')}",
            'sms': f"Processed: {message.get('original_message', {}).get('message', 'No message')[:50]}..."
        }
        
        # Publish to SNS
        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(sns_message),
            MessageStructure='json',
            MessageAttributes={
                'MessageId': {
                    'StringValue': message_id,
                    'DataType': 'String'
                },
                'ProcessingTime': {
                    'StringValue': message['processed_at'],
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Published to SNS: {response['MessageId']}")
        return response
        
    except Exception as e:
        logger.error(f"Error publishing to SNS: {str(e)}")
        raise e 