# Google OAuth Quick Start Guide

Get Google OAuth 2.0 working in CreatorIQ in 5 minutes.

---

## 1. Get Google Credentials (2 min)

1. Open https://console.cloud.google.com/
2. **Create a new project**
   - Click "Select a Project" → "New Project"
   - Name: "CreatorIQ" → Create
3. **Enable Google+ API**
   - Search bar: type "Google+ API" → Enable
4. **Create OAuth Credentials**
   - Go to "Credentials" (left sidebar)
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - Name: "CreatorIQ Frontend"
   - Authorized redirect URIs:
     ```
     http://localhost:8000/api/v1/auth/google/callback
     ```
   - Click "Create"
5. **Copy credentials**
   - You'll see: Client ID and Client Secret
   - Copy both (you'll need them in step 2)

---

## 2. Configure Backend (1 min)

1. Open `backend/.env` (create if doesn't exist)
2. Add these lines:
   ```env
   GOOGLE_AUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   GOOGLE_AUTH_CLIENT_SECRET=your-client-secret-here
   GOOGLE_AUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   ```
3. Replace values with your credentials from step 1

---

## 3. Start Services (1 min)

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Wait for: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Wait for: `Local: http://localhost:5173`

---

## 4. Test OAuth Flow (1 min)

1. Open http://localhost:5173 in browser
2. Click **"Continue with Google"** button
3. Sign in with your Google account
4. You'll be redirected back to CreatorIQ
5. If new user: See onboarding page
6. If returning: See dashboard

---

## Success! ✅

You now have Google OAuth working locally.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Google OAuth not configured" | Check `.env` file has `GOOGLE_AUTH_CLIENT_ID` |
| "Invalid redirect URI" | Ensure URI in `.env` matches Google Cloud Console exactly |
| Redirected to login after Google auth | Check backend logs for errors |
| Token not saved in localStorage | Check browser console for JavaScript errors |

---

## Production Deployment

When deploying to production:

1. **Update Google Cloud Console:**
   - Add production redirect URI:
     ```
     https://yourdomain.com/api/v1/auth/google/callback
     ```

2. **Update `.env`:**
   ```env
   GOOGLE_AUTH_REDIRECT_URI=https://yourdomain.com/api/v1/auth/google/callback
   FRONTEND_URL=https://yourdomain.com
   ```

3. **Enable HTTPS** (required by Google OAuth)

4. **Set strong JWT_SECRET:**
   ```env
   JWT_SECRET=generate-a-long-random-string-here
   ```

---

## Files Modified

- `backend/app/core/config.py` - Configuration
- `backend/app/models/identity.py` - Database fields
- `backend/app/api/router.py` - OAuth endpoints
- `backend/app/services/oauth.py` - OAuth logic (NEW)
- `frontend/src/App.jsx` - OAuth handler
- `backend/.env.example` - Documentation

---

## Testing API Directly

**Start OAuth flow:**
```bash
curl http://localhost:8000/api/v1/auth/google
```

Response:
```json
{
  "url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "token"
}
```

---

**Next:** Read [GOOGLE_OAUTH_IMPLEMENTATION.md](GOOGLE_OAUTH_IMPLEMENTATION.md) for detailed documentation.
