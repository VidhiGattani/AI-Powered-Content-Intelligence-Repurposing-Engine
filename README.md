# AI-Powered Content Repurposing Platform

An intelligent system that transforms long-form content (videos, articles, podcasts) into platform-optimized social media posts while maintaining the creator's unique voice and style.

## Architecture

- **Compute**: AWS Lambda (Python 3.11)
- **AI/ML**: Amazon Bedrock (Claude Sonnet 3.5, Titan Embeddings)
- **Storage**: Amazon S3, DynamoDB
- **Authentication**: Amazon Cognito
- **Infrastructure**: AWS CDK

## Project Structure

```
.
├── src/                    # Source code
│   └── utils/             # Shared utilities
│       ├── errors.py      # Error handling
│       ├── logger.py      # Structured logging
│       └── aws_clients.py # AWS client wrappers
├── tests/                 # Test suite
├── infrastructure/        # AWS CDK infrastructure
│   ├── app.py            # CDK app entry point
│   └── stacks/           # CDK stacks
│       ├── storage_stack.py    # S3 buckets
│       ├── database_stack.py   # DynamoDB tables
│       └── auth_stack.py       # Cognito User Pool
├── requirements.txt       # Python dependencies
└── cdk.json              # CDK configuration
```

## Setup

### Prerequisites

- Python 3.11+
- AWS CLI configured
- Node.js 18+ (for AWS CDK)
- AWS CDK CLI: `npm install -g aws-cdk`

### Installation

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

### Deployment

Deploy infrastructure:
```bash
cdk deploy --all
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

Format code:
```bash
black src/ tests/
```

Lint code:
```bash
flake8 src/ tests/
```

Type checking:
```bash
mypy src/
```

## Infrastructure

### S3 Buckets

- `style-vault-{account}` - User's past content for style learning
- `original-content-{account}` - Uploaded content for repurposing
- `transcripts-{account}` - Transcription results
- `generated-content-{account}` - AI-generated posts

### DynamoDB Tables

- `users` - User profiles
- `style_content` - Style content metadata
- `original_content` - Original content metadata
- `generated_content` - Generated content
- `scheduled_posts` - Scheduled posts

### Cognito

- User Pool: `content-repurposing-users`
- Authentication: Email + Password
- Token validity: 1 hour (access/id), 30 days (refresh)

## Environment Variables

```bash
AWS_REGION=us-east-1
LOG_LEVEL=INFO
COGNITO_USER_POOL_ID=<from deployment>
COGNITO_CLIENT_ID=<from deployment>
```

## License

Proprietary
