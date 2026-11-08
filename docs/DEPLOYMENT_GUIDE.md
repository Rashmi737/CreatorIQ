# CreatorIQ Production Cloud Deployment Guide

This guide details step-by-step production deployment procedures for the CreatorIQ platform across major cloud providers: **Render**, **Railway**, and **Amazon Web Services (AWS)**.

---

## 1. Environment Variables Reference

Configure these environment variables in your cloud hosting environment:

| Variable | Required | Description | Sample Production Value |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **Yes** | Server environment | `production` |
| `DATABASE_URL` | **Yes** | Database connection URI | `sqlite:////app/data/creatoriq.db` or PostgreSQL URI |
| `CORS_ORIGINS` | **Yes** | Allowed CORS origins (comma-separated) | `https://creatoriq.example.com` |
| `FRONTEND_URL` | **Yes** | Public frontend domain for redirects | `https://creatoriq.example.com` |
| `JWT_SECRET` | **Yes** | Cryptographic secret for signing tokens | `super-secure-high-entropy-jwt-secret-string` |
| `JWT_ALGORITHM` | No | JWT hashing algorithm | `HS256` |
| `ACCESS_TOKEN_MINUTES`| No | Token expiry lifetime | `60` |
| `YOUTUBE_API_KEY` | Optional | YouTube Data API v3 direct access key | `AIzaSyD-YourOfficialGoogleKey` |
| `RAPIDAPI_KEY` | Optional | RapidAPI key for real-time fallback scrapers | `0cc6aaff3dmsh99f564846b1c2cc...` |
| `GITHUB_TOKEN` | Optional | GitHub personal access token (60/hr -> 5,000/hr limit)| `ghp_YourGitHubToken` |
| `LINKEDIN_ACCESS_TOKEN`| Optional | LinkedIn Marketing / Member API OAuth token | `AQV...` |
| `INSTAGRAM_ACCESS_TOKEN`| Optional | Instagram Graph API access token | `EAA...` |

---

## 2. Option A: Render (Recommended Blueprint Deployment)

The repository includes a declarative `render.yaml` Blueprint file for turnkey orchestration.

### Steps:
1. Push your repository to GitHub or GitLab.
2. Log into [Render Dashboard](https://dashboard.render.com).
3. Navigate to **Blueprints** > **New Blueprint Instance**.
4. Select your CreatorIQ repository.
5. Render will detect `render.yaml` and configure:
   - **`creatoriq-backend`**: Docker Web Service with persistent 1GB SSD disk mounted at `/app/data` and automated health check `/api/v1/health`.
   - **`creatoriq-frontend`**: Static Web Site running `npm run build` and serving `frontend/dist` with SPA route rewrites to `/index.html`.
6. Fill in the sensitive environment variables (`YOUTUBE_API_KEY`, `RAPIDAPI_KEY`, `CORS_ORIGINS`).
7. Click **Apply**. Render will automatically build the images, attach storage, and launch both services with SSL certificates.

---

## 3. Option B: Railway Deployment

### Backend Setup:
1. Create a new Project in [Railway](https://railway.app).
2. Choose **Deploy from GitHub repo** and select the CreatorIQ repository.
3. In service settings, set **Root Directory** to `/backend`.
4. Add a **Persistent Volume**:
   - Mount path: `/app/data`
   - Size: 1 GB–5 GB
5. In **Variables**, add the environment variables listed in Section 1.
6. Set **Healthcheck Path** to `/api/v1/health`.
7. Generate a public domain (e.g., `https://creatoriq-api.up.railway.app`).

### Frontend Setup:
1. In the same project, add a new service from the same GitHub repo.
2. In service settings, set **Root Directory** to `/frontend`.
3. Set **Build Command** to `npm run build` and **Start Command** to `npx serve -s dist -l 5173` or deploy using the multi-stage `frontend/Dockerfile`.
4. In **Variables**, set:
   - `VITE_API_URL`: Your backend Railway domain (e.g., `https://creatoriq-api.up.railway.app`).
5. Update backend's `CORS_ORIGINS` to include your frontend Railway domain.

---

## 4. Option C: AWS Deployment (ECS / Fargate & S3 + CloudFront)

For high-scale production deployments on AWS:

### Architecture:
- **Frontend**: S3 Bucket configured for static website hosting with CloudFront CDN distribution and custom domain SSL (ACM).
- **Backend**: AWS ECS Fargate task running `backend/Dockerfile` behind an Application Load Balancer (ALB).
- **Storage**: AWS EFS volume mounted at `/app/data` for persistent SQLite storage, or RDS PostgreSQL.

### Step-by-Step:
1. **Push Container to ECR**:
   ```bash
   aws ecr create-repository --repository-name creatoriq-backend
   docker build -t creatoriq-backend ./backend
   docker tag creatoriq-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/creatoriq-backend:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/creatoriq-backend:latest
   ```
2. **Configure ECS Task Definition**:
   - Select Fargate launch type.
   - Container port: `8000`.
   - Add Health Check: `CMD-SHELL, curl -f http://localhost:8000/api/v1/health || exit 1`.
   - Attach EFS Volume to `/app/data`.
   - Add environment variables (`CORS_ORIGINS`, `JWT_SECRET`, `YOUTUBE_API_KEY`).
3. **Application Load Balancer**:
   - Target group protocol: `HTTP` on port `8000`.
   - Health check path: `/api/v1/health`.
   - Forward HTTPS port 443 to the target group.
4. **Deploy Frontend**:
   ```bash
   cd frontend
   npm run build
   aws s3 sync dist/ s3://creatoriq-frontend-bucket/ --delete
   aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
   ```

---

## 5. Option D: Local & Single-Server Docker Compose

For on-premises servers (Ubuntu / Debian / RHEL):

```bash
# Clone the repository
git clone https://github.com/CreatorIQ/creatoriq.git
cd creatoriq

# Copy production environment variables
cp .env.example .env
nano .env # configure YOUTUBE_API_KEY, CORS_ORIGINS, etc.

# Build and launch background daemon
docker compose up -d --build

# Verify container statuses and health
docker compose ps
docker compose logs -f backend
```

Access the dashboard at `http://localhost` (or server IP) and API documentation at `http://localhost:8000/docs`.
