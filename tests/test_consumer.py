import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from src.consumer.lambda_function import lambda_handler, process_message, publish_to_sns

class TestConsumerFunction:
    
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.aws_request_id = "test-request-id"
        return context
    
    @pytest.fixture
    def mock_sns(self):
        with patch('src.consumer.lambda_function.sns') as mock_sns:
            mock_sns.publish.return_value = {
                'MessageId': 'test-sns-message-id',
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            yield mock_sns
    
    def test_successful_message_processing(self, mock_context, mock_sns):
        """Test successful processing of SQS messages"""
        event = {
            'Records': [
                {
                    'messageId': 'test-message-id-1',
                    'body': json.dumps({
                        'message': 'Test message 1',
                        'priority': 'high',
                        'category': 'test'
                    })
                },
                {
                    'messageId': 'test-message-id-2',
                    'body': json.dumps({
                        'message': 'Test message 2',
                        'priority': 'low'
                    })
                }
            ]
        }
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': 'arn:aws:sns:region:account:test-topic'}):
            response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['processed_count'] == 2
        assert response_body['failed_count'] == 0
        assert len(response_body['processed_messages']) == 2
        
        # Verify SNS was called twice
        assert mock_sns.publish.call_count == 2
    
    def test_message_processing_with_error(self, mock_context, mock_sns):
        """Test handling of message processing errors"""
        mock_sns.publish.side_effect = Exception("SNS Error")
        
        event = {
            'Records': [
                {
                    'messageId': 'test-message-id',
                    'body': json.dumps({
                        'message': 'Test message'
                    })
                }
            ]
        }
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': 'arn:aws:sns:region:account:test-topic'}):
            response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 1
        assert len(response_body['failed_messages']) == 1
        assert 'SNS Error' in response_body['failed_messages'][0]['error']
    
    def test_process_message_function(self):
        """Test the process_message function"""
        message_body = {
            'message': 'Test message',
            'priority': 'high',
            'category': 'notification'
        }
        message_id = 'test-message-id'
        
        result = process_message(message_body, message_id)
        
        assert result['original_message'] == message_body
        assert result['message_id'] == message_id
        assert result['processor'] == 'consumer-lambda'
        assert result['version'] == '1.0'
        assert result['priority_level'] == 'high'
        assert result['category'] == 'notification'
        assert result['processing_status'] == 'completed'
        assert 'processed_at' in result
    
    def test_process_message_without_optional_fields(self):
        """Test process_message with minimal message body"""
        message_body = {
            'message': 'Test message'
        }
        message_id = 'test-message-id'
        
        result = process_message(message_body, message_id)
        
        assert result['original_message'] == message_body
        assert result['message_id'] == message_id
        assert result['processing_status'] == 'completed'
        assert 'priority_level' not in result
        assert 'category' not in result
    
    def test_publish_to_sns_success(self, mock_sns):
        """Test successful SNS publishing"""
        message = {
            'original_message': {'message': 'Test message'},
            'processed_at': '2023-01-01T00:00:00',
            'message_id': 'test-message-id',
            'processor': 'consumer-lambda'
        }
        message_id = 'test-message-id'
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': 'arn:aws:sns:region:account:test-topic'}):
            response = publish_to_sns(message, message_id)
        
        assert response['MessageId'] == 'test-sns-message-id'
        
        # Verify SNS publish was called correctly
        mock_sns.publish.assert_called_once()
        call_args = mock_sns.publish.call_args
        assert call_args[1]['TopicArn'] == 'arn:aws:sns:region:account:test-topic'
        assert call_args[1]['MessageStructure'] == 'json'
        
        # Verify message attributes
        message_attributes = call_args[1]['MessageAttributes']
        assert message_attributes['MessageId']['StringValue'] == message_id
        assert message_attributes['ProcessingTime']['StringValue'] == message['processed_at']
    
    def test_publish_to_sns_error(self, mock_sns):
        """Test SNS publishing error handling"""
        mock_sns.publish.side_effect = Exception("SNS Publishing Error")
        
        message = {
            'original_message': {'message': 'Test message'},
            'processed_at': '2023-01-01T00:00:00',
            'message_id': 'test-message-id'
        }
        message_id = 'test-message-id'
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': 'arn:aws:sns:region:account:test-topic'}):
            with pytest.raises(Exception, match="SNS Publishing Error"):
                publish_to_sns(message, message_id)
    
    def test_empty_records(self, mock_context):
        """Test handling of empty SQS event"""
        event = {'Records': []}
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 0
    
    def test_invalid_json_in_record(self, mock_context):
        """Test handling of invalid JSON in SQS record"""
        event = {
            'Records': [
                {
                    'messageId': 'test-message-id',
                    'body': 'invalid json'
                }
            ]
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['processed_count'] == 0
        assert response_body['failed_count'] == 1
        assert 'JSONDecodeError' in response_body['failed_messages'][0]['error']
    
    def test_sns_message_structure(self, mock_sns):
        """Test that SNS message has correct structure"""
        message = {
            'original_message': {'message': 'Test message'},
            'processed_at': '2023-01-01T00:00:00',
            'message_id': 'test-message-id'
        }
        message_id = 'test-message-id'
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': 'arn:aws:sns:region:account:test-topic'}):
            publish_to_sns(message, message_id)
        
        call_args = mock_sns.publish.call_args
        sns_message = json.loads(call_args[1]['Message'])
        
        assert 'default' in sns_message
        assert 'email' in sns_message
        assert 'sms' in sns_message
        assert 'Test message' in sns_message['email']
        assert 'Test message' in sns_message['sms'] 