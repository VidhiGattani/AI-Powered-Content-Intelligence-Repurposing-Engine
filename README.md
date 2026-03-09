# AI-Powered Content Repurposing Platform

An intelligent platform that transforms long-form content into optimized posts for multiple social media platforms using Amazon Bedrock's Claude 3.5 Sonnet AI model.

## 🚀 Live Demo

- **Frontend URL**: https://d3k9s112zjf39n.cloudfront.net
- **API Endpoint**: https://l69mf04tsj.execute-api.us-east-1.amazonaws.com/prod

## ✨ Features

### Core Functionality
- **Multi-Platform Content Generation**: Automatically repurpose content for LinkedIn, Twitter, Instagram, Facebook, and YouTube
- **AI-Powered Analysis**: Uses Amazon Bedrock Claude 3.5 Sonnet for intelligent content transformation
- **Style Profile Learning**: Upload sample content to teach the AI your unique writing style
- **Content Library**: Upload and manage source content (text, audio, video)
- **Real-time Generation**: Generate platform-optimized content with a single click
- **Content Editing**: Edit and refine generated content before publishing
- **SEO Optimization**: Generate titles, hashtags, and alt text for better reach
- **Smart Scheduling**: Schedule posts with optimal timing recommendations

### Technical Features
- **Serverless Architecture**: Built on AWS Lambda, API Gateway, and DynamoDB
- **Secure Authentication**: Amazon Cognito user management
- **Scalable Storage**: S3 for content storage, CloudFront for global delivery
- **Modern Frontend**: React + TypeScript + Tailwind CSS
- **Infrastructure as Code**: AWS CDK for reproducible deployments

## 🏗️ Architecture

```
Frontend (React + TypeScript)
    ↓
CloudFront CDN
    ↓
API Gateway
    ↓
Lambda Functions
    ↓
├── Amazon Bedrock (Claude 3.5 Sonnet)
├── Amazon Cognito (Authentication)
├── DynamoDB (Data Storage)
└── S3 (Content Storage)
```

## 🛠️ Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: AWS Lambda
- **AI Model**: Amazon Bedrock - Claude 3.5 Sonnet
- **Database**: Amazon DynamoDB
- **Storage**: Amazon S3
- **Authentication**: Amazon Cognito
- **API**: Amazon API Gateway
- **Infrastructure**: AWS CDK

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **Routing**: React Router

## 📋 Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS Account with appropriate permissions
- AWS CLI configured
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## 🚀 Deployment Guide

### 1. Clone the Repository

```bash
git clone <repository-url>
cd content-repurposing-platform
```

### 2. Backend Deployment

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Deploy infrastructure
cdk bootstrap  # First time only
cdk deploy --all --require-approval never
```

### 3. Frontend Deployment

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Deploy to S3
aws s3 sync dist s3://content-repurposing-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id <YOUR_DISTRIBUTION_ID> --paths "/*"
```

## 📖 Usage Guide

### 1. Sign Up / Sign In
- Navigate to the live demo URL
- Create an account with your email
- Sign in to access the dashboard

### 2. Build Your Style Profile
- Go to "Style Profile" page
- Upload 3-5 samples of your writing
- The AI learns your unique voice and tone

### 3. Upload Source Content
- Go to "Content Library"
- Upload your long-form content (text, audio, or video)
- Content is automatically processed and stored

### 4. Generate Platform-Specific Content
- Go to "Generate" page
- Select source content from your library
- Choose target platforms (LinkedIn, Twitter, etc.)
- Click "Generate" to create optimized posts
- Edit and refine as needed

### 5. Schedule Posts (Optional)
- Go to "Schedule" page
- Select generated content
- Choose platform and timing
- Get optimal posting time recommendations

## 🔑 Key Components

### Backend Services

- **Authentication Service**: User registration, login, token verification
- **Content Upload Handler**: Process and store uploaded content
- **Content Library Service**: Manage user content
- **Topic Extraction Service**: Extract key topics from content
- **Platform Agents**: AI-powered content generation for each platform
- **Content Generation Orchestrator**: Coordinate multi-platform generation
- **SEO Optimizer**: Generate titles, hashtags, and alt text
- **Scheduling Service**: Manage post scheduling

### Frontend Pages

- **Dashboard**: Overview and quick actions
- **Style Profile**: Upload and manage style samples
- **Content Library**: Upload and manage source content
- **Generate**: Create platform-specific content
- **Schedule**: Schedule posts with optimal timing

## 🔒 Security

- JWT-based authentication with Amazon Cognito
- Secure API endpoints with authorization checks
- CORS configured for browser security
- Environment variables for sensitive configuration
- IAM roles with least-privilege access

## 📊 AWS Services Used

- **Amazon Bedrock**: Claude 3.5 Sonnet for AI content generation
- **AWS Lambda**: Serverless compute for API handlers
- **Amazon API Gateway**: RESTful API management
- **Amazon DynamoDB**: NoSQL database for user data
- **Amazon S3**: Object storage for content files
- **Amazon CloudFront**: CDN for global content delivery
- **Amazon Cognito**: User authentication and management
- **AWS CDK**: Infrastructure as Code

## 🎯 Project Structure

```
.
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── contexts/        # React contexts (Auth)
│   │   ├── pages/           # Page components
│   │   └── services/        # API service layer
│   └── dist/                # Build output
├── infrastructure/          # AWS CDK infrastructure
│   ├── app.py              # CDK app entry point
│   └── stacks/             # CDK stack definitions
├── lambda_handlers/         # Lambda function handlers
│   └── src/                # Copied application code
├── src/                    # Core application code
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   └── utils/              # Utility functions
├── tests/                  # Unit tests
├── .kiro/                  # Kiro AI specs
├── cdk.json               # CDK configuration
└── requirements.txt       # Python dependencies
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run specific test file
pytest tests/test_services/test_platform_agents.py

# Run with coverage
pytest --cov=src tests/
```

## 🐛 Troubleshooting

### Backend Issues

**Lambda 500 Errors**
- Check CloudWatch Logs for detailed error messages
- Verify environment variables are set correctly
- Ensure IAM roles have necessary permissions

**Authentication Errors**
- Verify Cognito User Pool configuration
- Check JWT token expiration
- Confirm user email is verified

### Frontend Issues

**CORS Errors**
- Verify API Gateway CORS configuration
- Check CloudFront distribution settings
- Ensure proper headers in Lambda responses

**Build Errors**
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear build cache: `rm -rf dist`

## 📝 Environment Variables

### Backend (Lambda)
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_USER_POOL_CLIENT_ID`: Cognito Client ID
- `AWS_REGION`: AWS region (default: us-east-1)

### Frontend
- `VITE_API_URL`: API Gateway endpoint URL

## 🤝 Contributing

This project was developed as part of the AI for Bharat initiative. Contributions are welcome!

## 📄 License

This project is licensed under the MIT License.

## 👥 Authors

- Developed for AI for Bharat
- Powered by Amazon Bedrock and AWS

## 🙏 Acknowledgments

- Amazon Bedrock team for Claude 3.5 Sonnet access
- AWS for serverless infrastructure
- React and TypeScript communities

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review CloudWatch Logs for backend errors
3. Check browser console for frontend errors
4. Verify AWS service quotas and limits

---

**Built with ❤️ using AWS and AI**
