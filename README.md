# Event-Driven Architecture: API Gateway → Lambda → SQS → SNS (CloudFormation)

This repository contains the CloudFormation implementation of an event-driven architecture using AWS services.

## Architecture Overview

```
Client → API Gateway → Lambda → SQS → Lambda → SNS → Subscribers
```

## Components

- **API Gateway**: Receives HTTP requests
- **Lambda (Producer)**: Processes requests and sends messages to SQS
- **SQS**: Queues messages for asynchronous processing
- **Lambda (Consumer)**: Processes SQS messages and publishes to SNS
- **SNS**: Publishes notifications to subscribers

## Prerequisites

- AWS CLI configured
- Python 3.8+
- AWS SAM CLI (for local testing)

## Project Structure

```
event-driven-cf/
├── README.md
├── requirements.txt
├── template.yaml
├── src/
│   ├── producer/
│   │   └── lambda_function.py
│   └── consumer/
│       └── lambda_function.py
└── tests/
    ├── test_producer.py
    └── test_consumer.py
```

## Deployment

### Using AWS CLI

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build SAM application:
   ```bash
   sam build
   ```

3. Deploy the stack:
   ```bash
   sam deploy --guided
   ```

### Using CloudFormation Console

1. Upload the `template.yaml` file to CloudFormation console
2. Create stack with the template
3. Provide required parameters

## Testing

Run the tests:
```bash
pytest tests/
```

## Features

- Asynchronous message processing
- Dead letter queue for failed messages
- Comprehensive error handling
- CORS support
- Detailed logging and monitoring

## Cleanup

```bash
sam delete --stack-name event-driven-architecture
```

## API Endpoints

- `POST /message` - Send message to SQS queue

## Monitoring

- CloudWatch Logs for Lambda functions
- SQS metrics and alarms
- SNS delivery status 