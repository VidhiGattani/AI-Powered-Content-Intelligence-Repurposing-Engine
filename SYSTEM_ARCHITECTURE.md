# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         React Frontend Dashboard (Port 3000)              │ │
│  │  • Login/Signup  • Dashboard  • Style Profile            │ │
│  │  • Content Library  • Generate  • Schedule               │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS API GATEWAY                            │
│                    (REST API Endpoints)                         │
│  • /auth/*  • /content/*  • /generate/*                        │
│  • /style-content/*  • /seo/*  • /schedule/*                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS LAMBDA FUNCTIONS                       │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐     │
│  │   Auth   │  Style   │ Content  │ Generate │    SEO   │     │
│  │ Handler  │ Handler  │ Handler  │ Handler  │  Handler │     │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘     │
│  ┌──────────┬──────────────────────────────────────────┐      │
│  │ Schedule │     Python Business Logic Services       │      │
│  │ Handler  │  (13 services in src/services/)          │      │
│  └──────────┴──────────────────────────────────────────┘      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AWS SERVICES                             │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │   Amazon S3     │  │   DynamoDB      │  │   Cognito     │ │
│  │                 │  │                 │  │               │ │
│  │ • style-vault   │  │ • users         │  │ • User Pool   │ │
│  │ • original-     │  │ • style_content │  │ • JWT Tokens  │ │
│  │   content       │  │ • original_     │  │               │ │
│  │ • transcripts   │  │   content       │  │               │ │
│  │ • generated-    │  │ • generated_    │  │               │ │
│  │   content       │  │   content       │  │               │ │
│  │                 │  │ • scheduled_    │  │               │ │
│  │                 │  │   posts         │  │               │ │
│  └─────────────────┘  └─────────────────┘  └───────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │ Amazon Bedrock  │  │   Transcribe    │  │  CloudWatch   │ │
│  │                 │  │                 │  │               │ │
│  │ • Claude Sonnet │  │ • Speech-to-    │  │ • Logs        │ │
│  │   3.5           │  │   Text          │  │ • Metrics     │ │
│  │ • Titan         │  │ • Video/Audio   │  │ • Monitoring  │ │
│  │   Embeddings    │  │   Processing    │  │               │ │
│  │ • Knowledge     │  │                 │  │               │ │
│  │   Base          │  │                 │  │               │ │
│  └─────────────────┘  └─────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Authentication Flow
```
User → Frontend → API Gateway → Auth Lambda → Cognito
                                              ↓
                                         JWT Token
                                              ↓
                                    Store in LocalStorage
```

### 2. Style Profile Creation Flow
```
User uploads writing samples
         ↓
Frontend (base64 encode)
         ↓
API Gateway → Style Lambda
         ↓
Store in S3 (style-vault)
         ↓
Generate embeddings (Titan)
         ↓
Store in Bedrock Knowledge Base
         ↓
Update DynamoDB (style_content)
```

### 3. Content Upload & Processing Flow
```
User uploads video/audio/text
         ↓
Frontend (base64 encode)
         ↓
API Gateway → Content Lambda
         ↓
Store in S3 (original-content)
         ↓
If video/audio → Transcribe
         ↓
Store transcript in S3
         ↓
Extract topics (Claude Sonnet)
         ↓
Update DynamoDB (original_content)
```

### 4. Content Generation Flow
```
User selects content + platforms
         ↓
API Gateway → Generation Lambda
         ↓
Retrieve original content from S3
         ↓
Query Knowledge Base for style
         ↓
Extract style characteristics
         ↓
For each platform (parallel):
  ↓
  Build platform-specific prompt
  ↓
  Call Claude Sonnet (temp 0.7)
  ↓
  Validate against platform constraints
  ↓
Store in S3 (generated-content)
         ↓
Update DynamoDB (generated_content)
         ↓
Return to user
```

### 5. Scheduling Flow
```
User creates schedule
         ↓
API Gateway → Schedule Lambda
         ↓
Store in DynamoDB (scheduled_posts)
         ↓
EventBridge (cron) checks schedules
         ↓
Send notification when time arrives
```

## Component Responsibilities

### Frontend (React)
- **Purpose**: User interface and experience
- **Responsibilities**:
  - User authentication UI
  - File upload with drag-and-drop
  - Display generated content
  - Schedule management
  - Real-time status updates
- **Technology**: React 18, TypeScript, Tailwind CSS, Vite

### API Gateway
- **Purpose**: HTTP endpoint management
- **Responsibilities**:
  - Route requests to Lambda functions
  - CORS handling
  - Request/response transformation
  - API throttling
- **Endpoints**: 20+ REST endpoints

### Lambda Functions
- **Purpose**: Serverless compute
- **Responsibilities**:
  - Request validation
  - Business logic execution
  - Service orchestration
  - Error handling
- **Runtime**: Python 3.11
- **Timeout**: 30 seconds

### Business Logic Services (Python)
1. **AuthenticationService**: User management, JWT verification
2. **StyleProfileManager**: Style content upload, profile status
3. **ContentUploadHandler**: File upload, validation
4. **TranscriptionService**: Video/audio transcription
5. **TopicExtractionService**: AI topic extraction
6. **StyleRetrievalService**: RAG-based style matching
7. **PlatformAgents**: Platform-specific content generation
8. **ContentGenerationOrchestrator**: Multi-platform orchestration
9. **SEOOptimizer**: Title, hashtag, alt-text generation
10. **SchedulingService**: Post scheduling
11. **ContentEditingService**: Edit and approve content
12. **ContentLibraryService**: List, search, delete content
13. **IdempotencyService**: Prevent duplicate operations

### Storage (S3)
- **style-vault**: User writing samples
- **original-content**: Uploaded content
- **transcripts**: Transcription results
- **generated-content**: AI-generated posts
- **Features**: Encryption at rest, versioning

### Database (DynamoDB)
- **users**: User profiles
- **style_content**: Style content metadata
- **original_content**: Content metadata
- **generated_content**: Generated posts
- **scheduled_posts**: Scheduled posts
- **Features**: On-demand pricing, auto-scaling

### AI Services (Bedrock)
- **Claude Sonnet 3.5**: Content generation, topic extraction
- **Titan Embeddings**: Style embeddings
- **Knowledge Base**: Vector search for style matching

### Other Services
- **Cognito**: User authentication, JWT tokens
- **Transcribe**: Speech-to-text conversion
- **CloudWatch**: Logging, monitoring, metrics

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                            │
│                                                                 │
│  1. Network Layer                                              │
│     • HTTPS only                                               │
│     • API Gateway with throttling                              │
│     • CORS configured                                          │
│                                                                 │
│  2. Authentication Layer                                       │
│     • Cognito User Pool                                        │
│     • JWT tokens (1 hour expiry)                               │
│     • Password hashing                                         │
│                                                                 │
│  3. Authorization Layer                                        │
│     • IAM roles for Lambda                                     │
│     • Least-privilege policies                                 │
│     • Resource-based policies                                  │
│                                                                 │
│  4. Data Layer                                                 │
│     • S3 encryption at rest                                    │
│     • DynamoDB encryption                                      │
│     • Secure parameter store                                   │
│                                                                 │
│  5. Application Layer                                          │
│     • Input validation                                         │
│     • Error message sanitization                               │
│     • Request idempotency                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Scalability

### Auto-Scaling Components
- **Lambda**: Automatic scaling (up to 1000 concurrent executions)
- **DynamoDB**: On-demand capacity mode
- **S3**: Unlimited storage
- **API Gateway**: Handles millions of requests

### Performance Optimizations
- **Parallel Processing**: Multi-platform generation runs in parallel
- **Caching**: JWT token caching in frontend
- **Efficient Queries**: DynamoDB indexes for fast lookups
- **Lazy Loading**: Frontend loads data on demand

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUDWATCH                                 │
│                                                                 │
│  Logs                    Metrics                  Alarms        │
│  • Lambda execution     • Request count          • Error rate   │
│  • API Gateway          • Latency                • Throttling   │
│  • Error traces         • Success rate           • Cost         │
│  • User actions         • Resource usage         • Availability │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
Developer Machine
       ↓
   Git Commit
       ↓
   AWS CDK
       ↓
CloudFormation
       ↓
AWS Resources Created:
  • Lambda Functions
  • API Gateway
  • DynamoDB Tables
  • S3 Buckets
  • Cognito User Pool
  • IAM Roles
  • CloudWatch Logs
```

## Cost Optimization

### Free Tier Usage
- Lambda: 1M requests/month
- DynamoDB: 25 GB storage
- S3: 5 GB storage
- Cognito: 50,000 MAUs
- Transcribe: 60 minutes/month

### Pay-Per-Use
- Bedrock: ~$0.003 per 1K input tokens
- Lambda: $0.20 per 1M requests
- DynamoDB: $0.25 per GB-month
- S3: $0.023 per GB-month

## Technology Stack Summary

### Frontend
- React 18
- TypeScript
- Tailwind CSS
- Vite
- React Router
- Axios

### Backend
- Python 3.11
- AWS Lambda
- Amazon Bedrock
- AWS CDK
- Boto3

### Infrastructure
- API Gateway
- DynamoDB
- S3
- Cognito
- Transcribe
- CloudWatch

### AI/ML
- Claude Sonnet 3.5
- Titan Embeddings
- Bedrock Knowledge Base
