# How to Run the Content Repurposing Platform

## Simple 3-Step Guide

### Step 1: Deploy Backend to AWS ☁️

**If using PowerShell (Windows default):**
```powershell
.\deploy-backend.bat
```

**If using Command Prompt (CMD):**
```cmd
deploy-backend.bat
```

**Or run manually:**
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest tests/ -v
cd infrastructure
cdk deploy --all
```

This will:
- ✅ Activate Python virtual environment
- ✅ Install all Python dependencies
- ✅ Run 282 tests to verify everything works
- ✅ Deploy infrastructure to AWS (DynamoDB, S3, Lambda, API Gateway, Cognito)
- ✅ Output your API Gateway URL

**Important**: Copy the API Gateway URL from the output. It looks like:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

### Step 2: Configure Frontend 🎨

```bash
# Navigate to frontend folder
cd frontend

# Copy the example environment file
copy .env.example .env
```

Now edit `frontend/.env` and paste your API Gateway URL:
```
VITE_API_URL=https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

### Step 3: Start Frontend Dashboard 🚀

**If using PowerShell (Windows default):**
```powershell
.\start-frontend.bat
```

**If using Command Prompt (CMD):**
```cmd
start-frontend.bat
```

**Or run manually:**
```powershell
cd frontend
npm install
npm run dev
```

This will:
- ✅ Install Node.js dependencies (first time only)
- ✅ Start the development server
- ✅ Open the dashboard at http://localhost:3000

## Using the Platform

### 1. Create Account
- Visit http://localhost:3000
- Click "Sign up"
- Enter your email, password, and name
- You'll be automatically logged in

### 2. Build Style Profile
- Click "Style Profile" in the sidebar
- Upload at least 3 writing samples (.txt, .md, .pdf, .doc, .docx)
- Wait for "Profile Ready" status
- This teaches the AI your writing style

### 3. Upload Content
- Click "Content Library"
- Drag and drop a video, audio, or text file
- Wait for processing (transcription for video/audio)
- Content will show "transcribed" status when ready

### 4. Generate Content
- Click "Generate"
- Select your processed content
- Choose platforms (LinkedIn, Twitter, Instagram, YouTube Shorts)
- Click "Generate Content"
- Copy the generated content for each platform

### 5. Schedule Posts
- Click "Schedule"
- Enter the generated content ID
- Select platform and time
- Create schedule

## Troubleshooting

### Backend Issues

**Problem**: `deploy-backend.bat` fails
- **Solution**: Make sure you have Python 3.11+ installed
- Run: `python --version`
- Install from: https://www.python.org/downloads/

**Problem**: AWS credentials not configured
- **Solution**: Install AWS CLI and configure credentials
- Run: `aws configure`
- Enter your AWS Access Key ID and Secret Access Key

**Problem**: CDK bootstrap fails
- **Solution**: Make sure you have Node.js installed
- Run: `node --version`
- Install from: https://nodejs.org/

### Frontend Issues

**Problem**: `start-frontend.bat` fails
- **Solution**: Make sure you have Node.js 18+ installed
- Run: `node --version`
- Install from: https://nodejs.org/

**Problem**: "Failed to fetch" errors in browser
- **Solution**: Check that your API Gateway URL is correct in `frontend/.env`
- Make sure the backend is deployed successfully

**Problem**: CORS errors
- **Solution**: The API Gateway should have CORS enabled automatically
- If issues persist, check API Gateway CORS settings in AWS Console

### Authentication Issues

**Problem**: Can't sign up or sign in
- **Solution**: Check that Cognito User Pool was created
- Go to AWS Console → Cognito → User Pools
- Verify "content-repurposing-users" exists

**Problem**: Token expired errors
- **Solution**: Sign out and sign in again
- Tokens expire after 1 hour

## What You Need

### Software Requirements
- **Python 3.11+**: For backend services
- **Node.js 18+**: For frontend dashboard
- **AWS CLI**: For AWS credentials
- **AWS CDK**: Installed automatically with Node.js

### AWS Requirements
- **AWS Account**: Free tier is sufficient for testing
- **AWS Credentials**: Access Key ID and Secret Access Key
- **Bedrock Access**: Request access in AWS Console (required for AI features)
- **Permissions**: Lambda, DynamoDB, S3, Cognito, Bedrock, Transcribe, API Gateway

### Cost Estimate
- **Testing/Development**: ~$10-37/month
- **Production (moderate use)**: ~$85-255/month

Most AWS services have free tiers, so initial testing should be very cheap!

## Quick Commands Reference

### Backend
```bash
# Deploy backend
deploy-backend.bat

# Run tests only
pytest tests/ -v

# Deploy specific stack
cd infrastructure
cdk deploy ContentRepurposingApiStack
```

### Frontend
```bash
# Start frontend
start-frontend.bat

# Or manually:
cd frontend
npm install
npm run dev

# Build for production
npm run build
```

## File Locations

### Configuration Files
- Backend AWS config: `infrastructure/app.py`
- Frontend API config: `frontend/.env`
- CDK config: `cdk.json`

### Important Directories
- Backend services: `src/services/`
- Lambda handlers: `lambda_handlers/`
- Frontend pages: `frontend/src/pages/`
- Tests: `tests/`

## Next Steps

After getting the platform running:

1. **Customize Design**: Edit `frontend/tailwind.config.js` for colors
2. **Add Features**: Modify services in `src/services/`
3. **Deploy to Production**: Follow `RUNNING_THE_PROJECT.md` production section
4. **Monitor Usage**: Check AWS CloudWatch for logs and metrics
5. **Optimize Costs**: Review AWS Cost Explorer

## Getting Help

- **Setup Issues**: See `RUNNING_THE_PROJECT.md`
- **API Questions**: See `API_DOCUMENTATION.md`
- **Technical Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Project Overview**: See `PROJECT_COMPLETE.md`

## Success Checklist

You'll know everything is working when:
- ✅ Backend deploys without errors
- ✅ Frontend starts at http://localhost:3000
- ✅ You can sign up and log in
- ✅ Style profile uploads work
- ✅ Content uploads successfully
- ✅ Generated content appears
- ✅ Schedules are created

## That's It!

You now have a complete AI-powered content repurposing platform running locally with AWS backend.

**Enjoy repurposing your content! 🎉**
