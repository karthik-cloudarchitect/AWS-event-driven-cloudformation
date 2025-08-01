import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from src.producer.lambda_function import lambda_handler

class TestProducerFunction:
    
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.aws_request_id = "test-request-id"
        return context
    
    @pytest.fixture
    def mock_sqs(self):
        with patch('src.producer.lambda_function.sqs') as mock_sqs:
            mock_sqs.send_message.return_value = {
                'MessageId': 'test-message-id',
                'MD5OfMessageBody': 'test-md5'
            }
            yield mock_sqs
    
    def test_successful_message_send(self, mock_context, mock_sqs):
        """Test successful message sending to SQS"""
        event = {
            'body': json.dumps({
                'message': 'Test message',
                'priority': 'high',
                'category': 'test'
            })
        }
        
        with patch.dict(os.environ, {'QUEUE_URL': 'https://sqs.test.com/test-queue'}):
            response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['message'] == 'Message sent successfully'
        assert response_body['message_id'] == 'test-message-id'
        
        # Verify SQS was called correctly
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args
        assert call_args[1]['QueueUrl'] == 'https://sqs.test.com/test-queue'
        
        message_body = json.loads(call_args[1]['MessageBody'])
        assert message_body['message'] == 'Test message'
        assert message_body['priority'] == 'high'
        assert message_body['category'] == 'test'
    
    def test_missing_message_field(self, mock_context):
        """Test error handling when message field is missing"""
        event = {
            'body': json.dumps({
                'priority': 'high'
            })
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'Missing required field: message' in response_body['error']
    
    def test_invalid_json_body(self, mock_context):
        """Test error handling for invalid JSON"""
        event = {
            'body': 'invalid json'
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'Invalid JSON in request body' in response_body['error']
    
    def test_empty_body(self, mock_context):
        """Test error handling for empty body"""
        event = {}
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'Missing required field: message' in response_body['error']
    
    def test_sqs_error_handling(self, mock_context, mock_sqs):
        """Test error handling when SQS send fails"""
        mock_sqs.send_message.side_effect = Exception("SQS Error")
        
        event = {
            'body': json.dumps({
                'message': 'Test message'
            })
        }
        
        with patch.dict(os.environ, {'QUEUE_URL': 'https://sqs.test.com/test-queue'}):
            response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 500
        response_body = json.loads(response['body'])
        assert response_body['error'] == 'Internal server error'
    
    def test_message_with_optional_fields(self, mock_context, mock_sqs):
        """Test message sending with optional fields"""
        event = {
            'body': json.dumps({
                'message': 'Test message',
                'priority': 'low',
                'category': 'notification'
            })
        }
        
        with patch.dict(os.environ, {'QUEUE_URL': 'https://sqs.test.com/test-queue'}):
            response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        
        # Verify message attributes were set
        call_args = mock_sqs.send_message.call_args
        message_attributes = call_args[1]['MessageAttributes']
        assert 'RequestId' in message_attributes
        assert 'Timestamp' in message_attributes
        assert message_attributes['RequestId']['StringValue'] == 'test-request-id'
    
    def test_cors_headers(self, mock_context, mock_sqs):
        """Test that CORS headers are included in response"""
        event = {
            'body': json.dumps({
                'message': 'Test message'
            })
        }
        
        with patch.dict(os.environ, {'QUEUE_URL': 'https://sqs.test.com/test-queue'}):
            response = lambda_handler(event, mock_context)
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json' 