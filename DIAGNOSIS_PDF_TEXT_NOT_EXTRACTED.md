# Diagnosis: PDF Text Not Being Extracted

## Root Cause Found
The uploaded PDFs are stored in S3, but their text content is NOT being extracted.

## Current Flow (BROKEN)
1. User uploads PDF → Stored in S3
2. Generation handler tries to get content text
3. Looks for `transcript` or `content_text` attributes
4. Both are None for PDFs
5. Falls back to using filename: "Content about: BT phase 1 (1)"
6. Claude generates generic content based on filename only

## Why Content is Generic
Claude is receiving: "Content about: BT phase 1 (1)"
NOT the actual blockchain content from your PDF!

## Solution Options

### Option 1: Extract PDF text during upload (PROPER but COMPLEX)
- Modify content_upload_handler to extract PDF text
- Requires PyPDF2 or similar library
- Store extracted text in DynamoDB
- Risk: May break upload if PDF extraction fails

### Option 2: Extract PDF text during generation (SAFER)
- Keep upload simple (just store PDF)
- Extract text when generating content
- If extraction fails, use filename (current behavior)
- Lower risk - won't break uploads

### Option 3: Use AWS Textract (BEST but needs setup)
- AWS service for text extraction
- Handles complex PDFs well
- Requires additional AWS permissions
- Takes time to set up

## Recommended: Option 2 (Extract during generation)
- Safest approach
- Won't break existing uploads
- Can add PyPDF2 to Lambda layer
- Falls back gracefully if extraction fails
