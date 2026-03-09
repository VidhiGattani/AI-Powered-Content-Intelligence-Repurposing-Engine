# Running the Content Repurposing Platform

This guide will help you run the complete Content Repurposing Platform, including both the backend services and the frontend dashboard.

## Project Overview

The platform consists of:
- **Backend**: Python services with AWS infrastructure (Lambda, DynamoDB, S3, Bedrock, Cognito)
- **Frontend**: React + TypeScript dashboard with professional pastel design
- **API**: REST API endpoints connecting frontend to backend services

## Prerequisites

### Required Software
1. **Python 3.11+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Node.js 18+**
   - Download from [nodejs.org](https://nodejs.org/)
   - Verify: `node --version` and `npm --version`

3. **AWS CLI**
   - Install: `pip install awscli`
   - Configure: `aws configure`
   - You'll need AWS credentials with permissions for:
     - Lambda, DynamoDB, S3, Bedrock, Cognito, Transcribe, API Gateway

4. **AWS CDK**
   - Install: `npm install -g aws-cdk`
   - Verify: `cdk --version`

## Setup Instructions

### 1. Backend Setup

#### Install Python Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure AWS Credentials
```bash
# Configure AWS CLI with your credentials
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Default output format (json)
```

#### Deploy Infrastructure with CDK
```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cd infrastructure
cdk deploy --all

# This will create:
# - DynamoDB tables
# - S3 buckets
# - Cognito User Pool
# - API Gateway
# - Lambda functions
```

**Note**: The CDK deployment will output important values like:
- API Gateway URL
- Cognito User Pool ID
- Cognito Client ID

Save these values - you'll need them for the frontend configuration.

### 2. Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Configure Environment
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env and set your API URL
# VITE_API_URL=https://your-api-gateway-url.amazonaws.com
```

**Important**: Replace `your-api-gateway-url` with the actual API Gateway URL from your CDK deployment output.

#### Start Development Server
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Running the Complete System

### Option 1: Development Mode (Recommended for Testing)

Since the backend is serverless and deployed to AWS, you only need to run the frontend locally:

```bash
# 1. Make sure your AWS infrastructure is deployed
cd infrastructure
cdk deploy --all

# 2. Start the frontend
cd ../frontend
npm run dev
```

Visit `http://localhost:3000` in your browser.

### Option 2: Local Backend Testing

If you want to test backend services locally before deploying:

```bash
# Run tests
pytest tests/ -v

# Check code coverage
pytest tests/ --cov=src --cov-report=html
```

## Using the Dashboard

### 1. Sign Up / Sign In
- Navigate to `http://localhost:3000`
- Click "Sign up" to create a new account
- Enter your email, password, and name
- You'll be automatically signed in

### 2. Build Your Style Profile
- Go to "Style Profile" in the sidebar
- Upload at least 3 writing samples (.txt, .md, .pdf, .doc, .docx)
- Wait for the profile to show "Ready" status
- This helps the AI learn your writing style

### 3. Upload Content
- Go to "Content Library"
- Click the upload area
- Select a video, audio, or text file
- Wait for processing (transcription for video/audio)

### 4. Generate Repurposed Content
- Go to "Generate"
- Select a processed content item
- Choose target platforms (LinkedIn, Twitter, Instagram, YouTube Shorts)
- Click "Generate Content"
- View and copy the generated content for each platform

### 5. Schedule Posts
- Go to "Schedule"
- Enter the generated content ID
- Select platform and time
- Create the schedule

## Project Structure

```
content-repurposing-platform/
├── frontend/                    # React frontend dashboard
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── contexts/           # React contexts (Auth)
│   │   ├── pages/              # Page components
│   │   ├── services/           # API service layer
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── src/                        # Python backend services
│   ├── models/                 # Data models
│   ├── services/               # Business logic
│   └── utils/                  # Utilities
│
├── infrastructure/             # AWS CDK infrastructure
│   ├── stacks/                 # CDK stack definitions
│   └── app.py                  # CDK app entry point
│
├── lambda_handlers/            # Lambda function handlers
│   ├── auth.py                 # Authentication endpoints
│   ├── content.py              # Content management
│   ├── generation.py           # Content generation
│   ├── seo.py                  # SEO optimization
│   ├── style.py                # Style profile
│   └── scheduling.py           # Scheduling
│
├── tests/                      # Test suite
│   ├── test_services/          # Service tests
│   └── test_utils/             # Utility tests
│
└── .kiro/specs/                # Feature specifications
```

## Troubleshooting

### Frontend Issues

**Problem**: "Failed to fetch" errors
- **Solution**: Check that your API Gateway URL is correct in `.env`
- Verify the backend is deployed: `aws apigateway get-rest-apis`

**Problem**: CORS errors
- **Solution**: The API Gateway is configured with CORS. If issues persist, check the API Gateway CORS settings in AWS Console

### Backend Issues

**Problem**: "Access Denied" errors
- **Solution**: Verify your AWS credentials have the necessary permissions
- Check IAM roles and policies

**Problem**: Bedrock model not available
- **Solution**: Ensure you have access to Amazon Bedrock in your AWS region
- Request model access in the Bedrock console

**Problem**: Lambda timeout
- **Solution**: Increase timeout in `infrastructure/stacks/api_stack.py` (currently 30 seconds)

### Database Issues

**Problem**: DynamoDB table not found
- **Solution**: Ensure CDK deployment completed successfully
- Check tables exist: `aws dynamodb list-tables`

## Environment Variables

### Frontend (.env)
```
VITE_API_URL=https://your-api-gateway-url.amazonaws.com
```

### Backend (AWS Lambda Environment Variables)
These are automatically set by CDK:
- `USER_POOL_ID`: Cognito User Pool ID
- `USER_POOL_CLIENT_ID`: Cognito Client ID
- AWS service endpoints are auto-configured

## Testing

### Run Backend Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_services/test_authentication_service.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Frontend Testing
```bash
cd frontend

# Build for production
npm run build

# Preview production build
npm run preview
```

## Production Deployment

### Backend
```bash
cd infrastructure
cdk deploy --all --require-approval never
```

### Frontend
```bash
cd frontend

# Build for production
npm run build

# Deploy to S3 + CloudFront (recommended)
# 1. Create S3 bucket for static hosting
# 2. Upload dist/ folder to S3
# 3. Configure CloudFront distribution
# 4. Update VITE_API_URL to production API Gateway URL
```

## Cost Considerations

This platform uses AWS services that may incur costs:
- **Lambda**: Pay per request (generous free tier)
- **DynamoDB**: Pay per read/write (free tier available)
- **S3**: Pay per storage and requests (free tier available)
- **Bedrock**: Pay per API call (no free tier)
- **Transcribe**: Pay per minute of audio (free tier available)
- **Cognito**: Free for up to 50,000 MAUs

**Estimated monthly cost for light usage**: $10-50
**Estimated monthly cost for moderate usage**: $50-200

## Support

For issues or questions:
1. Check the API documentation: `API_DOCUMENTATION.md`
2. Review the implementation summary: `IMPLEMENTATION_SUMMARY.md`
3. Check AWS CloudWatch logs for backend errors
4. Review browser console for frontend errors

## Next Steps

1. **Customize the UI**: Modify colors and branding in `frontend/tailwind.config.js`
2. **Add Features**: Implement additional platforms or content types
3. **Improve AI**: Fine-tune prompts in service files
4. **Add Analytics**: Track usage and performance metrics
5. **Implement Webhooks**: Add real-time notifications

## Security Notes

- Never commit `.env` files or AWS credentials
- Use AWS Secrets Manager for sensitive data in production
- Enable MFA on your AWS account
- Regularly rotate access keys
- Use least-privilege IAM policies
- Enable CloudTrail for audit logging

## License

This project is for educational and commercial use.
