@echo off
echo ========================================
echo Deploying Frontend to AWS S3
echo ========================================

REM Build the frontend
echo.
echo Step 1: Building frontend...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo Build failed!
    exit /b %errorlevel%
)
cd ..

REM Create S3 bucket (if it doesn't exist)
echo.
echo Step 2: Creating S3 bucket...
aws s3 mb s3://content-repurposing-frontend --region us-east-1 2>nul
if %errorlevel% equ 0 (
    echo Bucket created successfully
) else (
    echo Bucket already exists or creation failed - continuing...
)

REM Configure bucket for static website hosting
echo.
echo Step 3: Configuring bucket for static website hosting...
aws s3 website s3://content-repurposing-frontend --index-document index.html --error-document index.html

REM Set bucket policy for public read access
echo.
echo Step 4: Setting bucket policy...
echo { > bucket-policy.json
echo   "Version": "2012-10-17", >> bucket-policy.json
echo   "Statement": [ >> bucket-policy.json
echo     { >> bucket-policy.json
echo       "Sid": "PublicReadGetObject", >> bucket-policy.json
echo       "Effect": "Allow", >> bucket-policy.json
echo       "Principal": "*", >> bucket-policy.json
echo       "Action": "s3:GetObject", >> bucket-policy.json
echo       "Resource": "arn:aws:s3:::content-repurposing-frontend/*" >> bucket-policy.json
echo     } >> bucket-policy.json
echo   ] >> bucket-policy.json
echo } >> bucket-policy.json

aws s3api put-bucket-policy --bucket content-repurposing-frontend --policy file://bucket-policy.json
del bucket-policy.json

REM Upload files to S3
echo.
echo Step 5: Uploading files to S3...
aws s3 sync frontend/dist/ s3://content-repurposing-frontend --delete --cache-control "public, max-age=31536000" --exclude "index.html"
aws s3 cp frontend/dist/index.html s3://content-repurposing-frontend/index.html --cache-control "no-cache"

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Your website is available at:
echo http://content-repurposing-frontend.s3-website-us-east-1.amazonaws.com
echo.
echo To set up CloudFront (recommended for HTTPS):
echo 1. Go to AWS CloudFront console
echo 2. Create a new distribution
echo 3. Set origin to: content-repurposing-frontend.s3-website-us-east-1.amazonaws.com
echo 4. Enable HTTPS
echo.
pause
