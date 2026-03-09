# Deployment Guide

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured with credentials
3. **Python 3.11+**: Installed on your system
4. **Node.js 18+**: Required for AWS CDK
5. **AWS CDK CLI**: Install globally with `npm install -g aws-cdk`

## Initial Setup

### 1. Clone and Install Dependencies

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

### 2. Configure AWS Credentials

```bash
aws configure
```

Provide:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Default output format (json)

### 3. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

Replace `ACCOUNT-ID` with your AWS account ID and `REGION` with your preferred region.

## Deployment

### Deploy All Stacks

```bash
cdk deploy --all
```

This will deploy:
1. **StorageStack**: S3 buckets for content storage
2. **DatabaseStack**: DynamoDB tables for metadata
3. **AuthStack**: Cognito User Pool for authentication

### Deploy Individual Stacks

```bash
# Deploy storage only
cdk deploy ContentRepurposingStorageStack

# Deploy database only
cdk deploy ContentRepurposingDatabaseStack

# Deploy auth only
cdk deploy ContentRepurposingAuthStack
```

## Post-Deployment Configuration

### 1. Retrieve Stack Outputs

After deployment, CDK will output important values. Save these to your `.env` file:

```bash
# Get Cognito User Pool ID
aws cognito-idp list-user-pools --max-results 10

# Get Cognito Client ID
aws cognito-idp list-user-pool-clients --user-pool-id YOUR_USER_POOL_ID

# Get S3 bucket names
aws s3 ls | grep -E "(style-vault|original-content|transcripts|generated-content)"
```

### 2. Update Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Edit `.env` with the values from step 1.

### 3. Create Bedrock Knowledge Base

The Knowledge Base must be created manually through the AWS Console:

1. Go to Amazon Bedrock Console
2. Navigate to Knowledge Bases
3. Click "Create knowledge base"
4. Configure:
   - Name: `content-repurposing-style-kb`
   - Vector store: Amazon OpenSearch Serverless
   - Embedding model: Amazon Titan Embeddings G1
5. Note the Knowledge Base ID and add to `.env`

## Verification

### Test Infrastructure

```bash
# Run tests
pytest tests/ -v

# Check CDK diff (should show no changes)
cdk diff
```

### Test AWS Resources

```bash
# List S3 buckets
aws s3 ls

# List DynamoDB tables
aws dynamodb list-tables

# Describe Cognito User Pool
aws cognito-idp describe-user-pool --user-pool-id YOUR_USER_POOL_ID
```

## Updating Infrastructure

### Make Changes

1. Edit CDK stack files in `infrastructure/stacks/`
2. Review changes: `cdk diff`
3. Deploy changes: `cdk deploy --all`

### Rollback

If deployment fails or you need to rollback:

```bash
# Destroy all stacks
cdk destroy --all

# Redeploy from last known good state
cdk deploy --all
```

## Monitoring

### CloudWatch Logs

All Lambda functions log to CloudWatch. View logs:

```bash
aws logs tail /aws/lambda/FUNCTION_NAME --follow
```

### CloudWatch Metrics

Monitor key metrics:
- Lambda invocations and errors
- DynamoDB read/write capacity
- S3 request counts
- Cognito authentication attempts

## Cost Optimization

### Development Environment

For development, consider:
- Using DynamoDB on-demand pricing
- Setting S3 lifecycle policies to delete old test data
- Deleting unused resources: `cdk destroy --all`

### Production Environment

For production:
- Enable S3 Intelligent-Tiering
- Use DynamoDB auto-scaling
- Set up CloudWatch alarms for cost anomalies
- Review AWS Cost Explorer regularly

## Troubleshooting

### CDK Bootstrap Issues

```bash
# Re-bootstrap if needed
cdk bootstrap --force
```

### Permission Errors

Ensure your IAM user/role has:
- CloudFormation full access
- S3 full access
- DynamoDB full access
- Cognito full access
- Lambda full access
- IAM role creation permissions

### Stack Deletion Issues

If stack deletion fails:

```bash
# Check stack events
aws cloudformation describe-stack-events --stack-name STACK_NAME

# Force delete (use with caution)
aws cloudformation delete-stack --stack-name STACK_NAME
```

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Rotate AWS credentials regularly**
3. **Enable MFA on AWS account**
4. **Use least privilege IAM policies**
5. **Enable CloudTrail for audit logging**
6. **Encrypt all data at rest and in transit**
7. **Regularly review security groups and IAM policies**

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review CDK documentation: https://docs.aws.amazon.com/cdk/
3. Check AWS service health dashboard
4. Contact AWS Support if needed
