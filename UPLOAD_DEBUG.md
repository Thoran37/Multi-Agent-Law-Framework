# Upload 422 Error - Troubleshooting & Fix

## Problem Summary
**Error:** `"POST /api/upload HTTP/1.1" 422 Unprocessable Entity`

This error occurs when FastAPI cannot parse the incoming request according to the endpoint's parameter definitions.

## Root Causes & Solutions

### 1. ✅ FIXED: Parameter Definition Issue
**Problem:** The original endpoint had `Optional[str] = Form(None)` for jurisdiction, which can cause parsing issues.

**Solution Applied:**
```python
# BEFORE (causes issues):
async def upload_document(files: List[UploadFile] = File(...), 
                         jurisdiction: Optional[str] = Form(None)):

# AFTER (works correctly):
async def upload_document(files: List[UploadFile] = File(...), 
                         jurisdiction: str = Form(default="India")):
```

### 2. Client-Side Fix: Console Logging
**Update to App.js handleUpload function to better see errors:**

```javascript
catch (error) {
  console.error('Upload error details:', error.response?.data || error.message);
  toast.error('Error uploading documents: ' + (error.response?.data?.detail || error.message));
}
```

## Testing the Fix

### Method 1: Python/Requests (Recommended)
```powershell
python -c "
import requests

# Single file
files = {'files': open('test_case.txt', 'rb')}
data = {'jurisdiction': 'India'}
response = requests.post('http://127.0.0.1:8000/api/upload', files=files, data=data)
print('Status:', response.status_code)
print('Response:', response.json())
"
```

### Method 2: JavaScript/Axios (Browser Console)
```javascript
const formData = new FormData();
formData.append('files', document.getElementById('file-input').files[0]);
formData.append('jurisdiction', 'India');

axios.post('http://127.0.0.1:8000/api/upload', formData)
  .then(r => console.log('Success:', r.data))
  .catch(e => console.error('Error:', e.response?.data));
```

## Common Issues & Solutions

### Issue 1: Still Getting 422 Error
**Cause:** Browser cache or old endpoint definition

**Solution:**
1. Hard refresh frontend: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)
2. Restart backend server:
   ```powershell
   # Kill existing process
   Get-Process python | Stop-Process -Force
   
   # Restart
   cd backend
   python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
   ```

### Issue 2: "At least one file must be provided"
**Cause:** No files being sent in FormData

**Solution:** Verify in browser DevTools Network tab that files are present in the request

### Issue 3: Files not appearing in FormData
**Cause:** File input not properly populated

**Solution:**
```javascript
// Debug in browser console
const input = document.getElementById('file-input');
console.log('Files:', input.files);
console.log('File count:', input.files.length);
```

### Issue 4: UTF-8 Encoding Error
**Cause:** Text files saved without UTF-8 encoding (BOM header like 0xFF)

**Solution:** Ensure files are saved as UTF-8:
```powershell
python -c "
with open('your_file.txt', 'w', encoding='utf-8') as f:
    f.write('Your content here')
"
```

## Verification Checklist

Before attempting upload again, verify:

- [ ] Backend is running: `netstat -ano | findstr :8000` shows a LISTENING process
- [ ] Frontend environment has `REACT_APP_BACKEND_URL=http://127.0.0.1:8000`
- [ ] Files are selected before clicking Upload
- [ ] At least one file is selected (not empty)
- [ ] File is a valid PDF or TXT file
- [ ] Text files are UTF-8 encoded (no BOM)
- [ ] Browser console shows no CORS errors
- [ ] No 422 error in Network tab

## How to Debug in Browser

1. Open Developer Tools (`F12`)
2. Go to **Network** tab
3. Select a file and click Upload
4. Find the `POST /api/upload` request
5. Check:
   - **Status:** Should be 200 (not 422)
   - **Request Headers:** Should include `Content-Type: multipart/form-data`
   - **Request Payload:** Should show files and jurisdiction
   - **Response:** Should show `case_id` and `raw_text`

## Files Modified

- `backend/server.py` - Fixed endpoint parameter definition
- `frontend/src/App.js` - Added better error logging

## Testing Files

Created `test_case.txt` in workspace root for testing. Use it to verify upload functionality:

```powershell
python -c "
import requests
files = {'files': open('test_case.txt', 'rb')}
data = {'jurisdiction': 'India'}
response = requests.post('http://127.0.0.1:8000/api/upload', files=files, data=data)
print('Status:', response.status_code)
print(response.json())
"
```

## Next Steps

1. **Test with Python first** - Verify backend works
2. **Test with Browser DevTools** - Debug frontend integration
3. **Check console logs** - Look for JavaScript errors
4. **Monitor backend logs** - Look for server-side errors

## API Endpoint Details

### Upload Endpoint
```
POST /api/upload
Content-Type: multipart/form-data

Parameters:
- files: File[] (multiple files, required)
- jurisdiction: string (optional, defaults to "India")

Success Response (200):
{
  "case_id": "uuid-string",
  "raw_text": "extracted text preview...",
  "message": "Successfully uploaded N document(s)"
}

Error Response (4xx/5xx):
{
  "detail": "error message"
}
```

## Performance Notes

- Single file upload: ~1-3 seconds
- Multiple files (3+): ~3-5 seconds
- OCR on scanned PDF: +5-10 seconds (first page)
- RAG indexing: +2-3 seconds
