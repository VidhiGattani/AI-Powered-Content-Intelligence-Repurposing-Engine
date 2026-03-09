# SYSTEM ARCHITECTURE DIAGRAM

## Detailed Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                 │
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐             │
│  │   Browser     │  │   Mobile      │  │   Desktop     │             │
│  │   (Web)       │  │   (iOS/App)   │  │   (Electron)  │             │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘             │
│          │                   │                   │                     │
│          └───────────────────┴───────────────────┘                     │
│                              │                                         │
│                    React + TypeScript                                  │
│                    Tailwind + shadcn/ui                                │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CDN LAYER (CloudFront)                          │
│                    Static Assets + Edge Caching                        │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (REST + WebSocket)                     │
│                                                                         │
│  Endpoints:                                                             │
│  • POST /api/style/upload        • POST /api/content/upload            │
│  • POST /api/content/generate    • GET  /api/content/:id               │
│  • POST /api/schedule            • GET  /api/analytics                 │
│  • POST /api/seo/optimize        • GET  /api/trends                    │
│                                                                         │
│  Features: Rate Limiting, Authentication, CORS, Logging                 │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Lambda:        │  │   Lambda:        │  │   Lambda:        │
│   Upload         │  │   Process        │  │   Generate       │
│   Handler        │  │   Content        │  │   Content        │
│                  │  │                  │  │                  │
│  • Auth check    │  │  • Transcribe    │  │  • RAG query     │
│  • File validate │  │  • Extract topics│  │  • Agent invoke  │
│  • S3 upload     │  │  • Metadata save │  │  • Result format │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│                  │  │                  │  │                  │
│   Amazon S3      │  │  Amazon          │  │   DynamoDB       │
│                  │  │  Transcribe      │  │                  │
│  Buckets:        │  │                  │  │  Tables:         │
│  • style-vault/  │  │  • Video → Text  │  │  • users         │
│  • uploads/      │  │  • Audio → Text  │  │  • content       │
│  • generated/    │  │  • Timestamps    │  │  • schedules     │
│                  │  │                  │  │  • analytics     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                                            │
        └────────────────────┬───────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AMAZON BEDROCK LAYER                            │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    KNOWLEDGE BASE (RAG)                           │ │
│  │                                                                   │ │
│  │  ┌──────────────────┐          ┌──────────────────────────────┐ │ │
│  │  │  Titan           │          │   Vector Database            │ │ │
│  │  │  Embeddings      │  ───────>│   (OpenSearch Serverless)    │ │ │
│  │  │  v2              │          │                              │ │ │
│  │  │                  │          │  Stores:                     │ │ │
│  │  │  Converts text   │          │  • User style embeddings     │ │ │
│  │  │  to 1024-dim     │          │  • Vocabulary patterns       │ │ │
│  │  │  vectors         │          │  • Tone fingerprints         │ │ │
│  │  └──────────────────┘          │  • Structural templates      │ │ │
│  │                                 └──────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Retrieval Flow:                                                  │ │
│  │  1. New content → Embedding                                       │ │
│  │  2. Semantic search → Top 3 matches                               │ │
│  │  3. Return style snippets                                         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     BEDROCK AGENTS                                │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Agent 1: LinkedIn Professional Narrator                    │ │ │
│  │  │                                                             │ │ │
│  │  │  Input: Original content + Style patterns                   │ │ │
│  │  │  Behavior:                                                  │ │ │
│  │  │  • Focus on thought leadership                              │ │ │
│  │  │  • Professional but conversational                          │ │ │
│  │  │  • Start with hook                                          │ │ │
│  │  │  • End with discussion prompt                               │ │ │
│  │  │  Output: 150-250 word LinkedIn post                         │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Agent 2: Twitter Thread Architect                          │ │ │
│  │  │                                                             │ │ │
│  │  │  Input: Original content + Style patterns                   │ │ │
│  │  │  Behavior:                                                  │ │ │
│  │  │  • Extract 5-7 "value bombs"                                │ │ │
│  │  │  • Create curiosity-driven thread                           │ │ │
│  │  │  • Each tweet <280 chars                                    │ │ │
│  │  │  • End with CTA                                             │ │ │
│  │  │  Output: 5-7 tweet thread                                   │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Agent 3: Instagram Captivator                              │ │ │
│  │  │                                                             │ │ │
│  │  │  Input: Original content + Style patterns                   │ │ │
│  │  │  Behavior:                                                  │ │ │
│  │  │  • Emotional, relatable tone                                │ │ │
│  │  │  • Short paragraphs                                         │ │ │
│  │  │  • Liberal emoji use                                        │ │ │
│  │  │  • Story-driven                                             │ │ │
│  │  │  Output: 100-150 word caption                               │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Agent 4: YouTube Shorts Script Generator                   │ │ │
│  │  │                                                             │ │ │
│  │  │  Input: Original content + Style patterns                   │ │ │
│  │  │  Behavior:                                                  │ │ │
│  │  │  • Hook in first 3 seconds                                  │ │ │
│  │  │  • Spoken language (not written)                            │ │ │
│  │  │  • 30-60 second duration                                    │ │ │
│  │  │  • Visual cues included                                     │ │ │
│  │  │  Output: Timestamped script                                 │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    FOUNDATION MODELS                              │ │
│  │                                                                   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  Claude Sonnet 4.5 (Primary Generation Model)           │   │ │
│  │  │                                                          │   │ │
│  │  │  Model ID: anthropic.claude-sonnet-4-5-20250929         │   │ │
│  │  │  Max Tokens: 8192 (output)                              │   │ │
│  │  │  Temperature: 0.7 (creative but controlled)             │   │ │
│  │  │                                                          │   │ │
│  │  │  Used for:                                               │   │ │
│  │  │  • Main content generation                               │   │ │
│  │  │  • SEO title variations                                  │   │ │
│  │  │  • Hashtag suggestions                                   │   │ │
│  │  │  • Alt-text generation                                   │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                                │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │   News API       │  │  Google Trends   │  │   FFmpeg         │    │
│  │                  │  │                  │  │   (Optional)     │    │
│  │  • Breaking news │  │  • Trending      │  │                  │    │
│  │  • Topic trends  │  │    topics        │  │  • Video cutting │    │
│  │  • Newsjacking   │  │  • Search volume │  │  • Transcript    │    │
│  │    opportunities │  │  • Interest over │  │    sync editing  │    │
│  │                  │  │    time          │  │                  │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

```

## Data Flow Diagram

### Flow 1: Style Profile Creation
```
User Uploads Past Content
         │
         ▼
    Lambda: Upload
         │
         ├──> S3: Store originals
         │
         ├──> Extract text content
         │
         ▼
  Titan Embeddings
         │
         ▼
Knowledge Base: Store vectors
         │
         ▼
  DynamoDB: Mark profile as ready
```

### Flow 2: Content Generation
```
User Uploads New Content
         │
         ▼
    Lambda: Upload
         │
         ├──> S3: Store file
         │
         └──> If video/audio:
              Amazon Transcribe
                    │
                    ▼
              Extract transcript
         │
         ▼
    Lambda: Process
         │
         ├──> Extract key topics
         ├──> Identify main points
         └──> Store metadata (DynamoDB)
         │
         ▼
User Selects Platforms
         │
         ▼
    Lambda: Generate
         │
         ├──> Query Knowledge Base
         │    (Retrieve style patterns)
         │
         ├──> For each platform:
         │    │
         │    ├──> Construct prompt with:
         │    │    • Original content
         │    │    • Style patterns
         │    │    • Platform agent instructions
         │    │
         │    └──> Invoke Claude Sonnet
         │         (via Bedrock)
         │
         ▼
  Generated Content
         │
         ├──> Store in S3
         └──> Return to user
         │
         ▼
User Reviews & Edits
         │
         ▼
User Requests SEO Optimization
         │
         ├──> Generate 5 title variants
         ├──> Generate semantic hashtags
         └──> Generate alt-text
         │
         ▼
User Schedules Post
         │
         └──> Store in DynamoDB
              (scheduled_posts table)
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                          │
│                                                             │
│  Layer 1: Authentication                                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  AWS Cognito User Pool                                │ │
│  │  • Email/password auth                                │ │
│  │  • JWT tokens                                         │ │
│  │  • MFA support                                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 2: Authorization                                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  IAM Roles & Policies                                 │ │
│  │  • Lambda execution roles                             │ │
│  │  • S3 bucket policies                                 │ │
│  │  • Bedrock access policies                            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 3: Data Protection                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  • S3 encryption at rest (AES-256)                    │ │
│  │  • DynamoDB encryption                                │ │
│  │  • HTTPS/TLS in transit                               │ │
│  │  • CloudFront signed URLs                             │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 4: Rate Limiting & Monitoring                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  • API Gateway throttling                             │ │
│  │  • CloudWatch logs & alarms                           │ │
│  │  • X-Ray tracing                                      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Cost Optimization

```
┌─────────────────────────────────────────────────────────────┐
│                  COST STRUCTURE                             │
│                                                             │
│  Compute:                                                   │
│  • Lambda (pay per invocation)                              │
│  • 1M requests/month free tier                              │
│  • ~$0.20 per 1M requests after                             │
│                                                             │
│  Storage:                                                   │
│  • S3: ~$0.023/GB                                           │
│  • DynamoDB: On-demand pricing                              │
│                                                             │
│  AI Services:                                               │
│  • Bedrock Claude Sonnet: $3 per 1M input tokens            │
│  • Titan Embeddings: $0.10 per 1M tokens                    │
│  • Transcribe: $0.024/minute                                │
│                                                             │
│  Estimated Cost per User (Monthly):                         │
│  • 50 content repurposing sessions                          │
│  • ~$2-5 per user                                           │
│                                                             │
│  Optimization Strategies:                                   │
│  ✓ Cache embeddings to reduce Titan calls                   │
│  ✓ Batch processing where possible                          │
│  ✓ Use S3 lifecycle policies                                │
│  ✓ Implement request throttling                             │
└─────────────────────────────────────────────────────────────┘
```

