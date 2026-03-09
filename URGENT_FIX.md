# URGENT: Fix Mock Mode Issue

## The Problem
Your `.env` file is in a OneDrive folder, which is causing caching issues. The file shows different content depending on how it's accessed.

## The Solution

### Option 1: Force Refresh (Quick Fix)

1. **Stop the dev server** (Ctrl+C in the terminal running npm)

2. **Clear Vite cache:**
   ```powershell
   cd frontend
   Remove-Item -Recurse -Force node_modules\.vite
   ```

3. **Clear browser cache:**
   - Press Ctrl+Shift+Delete
   - Select "All time"
   - Check "Cached images and files"
   - Click "Clear data"

4. **Restart dev server:**
   ```powershell
   npm run dev
   ```

5. **Hard refresh browser:**
   - Press Ctrl+Shift+R (or Ctrl+F5)

### Option 2: Hardcode Production Mode (Guaranteed Fix)

If Option 1 doesn't work, hardcode the production settings:

**Edit `frontend/src/services/api.ts`:**

Find this line (around line 5):
```typescript
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true'
```

Replace it with:
```typescript
const MOCK_MODE = false  // HARDCODED: Always use production API
```

Also find this line (around line 4):
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
```

Replace it with:
```typescript
const API_BASE_URL = 'https://l69mf04tsj.execute-api.us-east-1.amazonaws.com/prod'  // HARDCODED
```

Then restart the dev server.

## Verify It's Working

After applying the fix, open browser console (F12) and you should see:

```
=== API CONFIGURATION ===
Computed MOCK_MODE: false
Using REAL API
```

When you sign up or log in, you should see API calls to:
```
https://l69mf04tsj.execute-api.us-east-1.amazonaws.com/prod/auth/...
```

## About Content Generation

Even with the real API working, content generation requires:

1. **Bedrock Access Approved** - You submitted the use case form, AWS typically takes 1-3 business days to approve
2. **Until approved**, you'll get errors when trying to generate content
3. **Other features work**: Sign up, login, upload content, style profile, scheduling

## Next Steps

1. Apply Option 1 or Option 2 above
2. Test sign up/login to verify real API is working
3. Wait for Bedrock approval email from AWS
4. Once approved, content generation will work automatically
