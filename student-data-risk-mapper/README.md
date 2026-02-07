# Student Data Risk Mapper

A privacy risk assessment tool for K-12 school districts to inventory edtech systems and evaluate student data handling practices.

## Features

- **Microsoft Entra ID SSO** - Secure authentication using your district's Microsoft 365 tenant
- **System Inventory** - Track all edtech vendors, apps, and integrations
- **Guided Risk Assessment** - Multi-step questionnaire covering data types, storage, security, and integrations
- **Explainable Scoring** - Clear 0-100 risk scores with reason codes explaining each factor
- **Data Privacy Label** - Visual summary of each system's privacy posture
- **Dashboard & Filters** - Search, filter by risk tier, data types, and more
- **Sensitive Data Heatmap** - Visual matrix of systems vs. sensitive data types
- **PDF Export** - Generate assessment reports for individual systems
- **CSV Export** - Full inventory export for admins
- **Audit Logging** - Track all user actions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Microsoft Entra ID (Azure AD) tenant with admin access to register an app

### 1. Clone and Configure

```bash
cd student-data-risk-mapper
cp .env.example .env
```

Edit `.env` with your settings (see [Entra ID Setup](#microsoft-entra-id-setup) below).

### 2. Start Services

```bash
# Start database and app
docker-compose up -d

# Run database migrations
docker-compose --profile migrate run --rm migrate

# View logs
docker-compose logs -f app
```

### 3. Access the Application

Open http://localhost:8000 and sign in with your Microsoft account.

## Microsoft Entra ID Setup

### 1. Register an Application

1. Go to [Azure Portal](https://portal.azure.com) → Microsoft Entra ID → App registrations
2. Click **New registration**
3. Configure:
   - **Name**: Student Data Risk Mapper
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URI**: Web → `http://localhost:8000/auth/callback` (update for production)
4. Click **Register**

### 2. Configure Authentication

1. In your app registration, go to **Authentication**
2. Under **Implicit grant and hybrid flows**, ensure **ID tokens** is checked
3. Set **Logout URL**: `http://localhost:8000/auth/login`
4. Save changes

### 3. Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and set expiration
4. **Copy the secret value immediately** - you won't see it again

### 4. Configure Group Claims (Optional)

For role-based access (admin/auditor), configure group claims:

1. Go to **Token configuration**
2. Click **Add groups claim**
3. Select **Security groups**
4. Under **ID token**, check **Group ID**
5. Save

Then note the Object IDs of your admin and auditor groups for the environment variables.

### 5. Update Environment Variables

```env
ENTRA_CLIENT_ID=<Application (client) ID>
ENTRA_CLIENT_SECRET=<Client secret value>
ENTRA_TENANT_ID=<Directory (tenant) ID>

# Optional: Role mapping via group IDs
ENTRA_ADMIN_GROUP_ID=<Object ID of admin group>
ENTRA_AUDITOR_GROUP_ID=<Object ID of auditor group>
```

### 6. API Permissions

The default permissions (User.Read) are sufficient. No admin consent required.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Random string (32+ chars) for session signing |
| `BASE_URL` | Yes | Public URL of your app (e.g., `https://risk.district.edu`) |
| `DATABASE_URL` | Yes | PostgreSQL async connection string |
| `DATABASE_URL_SYNC` | Yes | PostgreSQL sync connection string (for migrations) |
| `ENTRA_CLIENT_ID` | Yes | Azure app registration client ID |
| `ENTRA_CLIENT_SECRET` | Yes | Azure app registration client secret |
| `ENTRA_TENANT_ID` | Yes | Azure AD tenant ID |
| `ENTRA_ADMIN_GROUP_ID` | No | Object ID of Entra group for admin role |
| `ENTRA_AUDITOR_GROUP_ID` | No | Object ID of Entra group for auditor role |

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Production Deployment

### Cloudflare Tunnel Setup

1. Install cloudflared on your Linux VM:
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

2. Authenticate and create tunnel:
```bash
cloudflared tunnel login
cloudflared tunnel create student-risk-mapper
```

3. Configure the tunnel (`~/.cloudflared/config.yml`):
```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: risk.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

4. Start the tunnel:
```bash
cloudflared tunnel run student-risk-mapper
```

5. Add DNS record in Cloudflare dashboard pointing to your tunnel.

### Security Recommendations

1. **HTTPS**: Always use HTTPS in production (Cloudflare handles this)
2. **Database Backups**: Set up regular PostgreSQL backups
3. **Secret Rotation**: Rotate `SECRET_KEY` and Entra client secret periodically
4. **Network Isolation**: Keep Postgres on internal network only
5. **Monitoring**: Set up log aggregation and alerting
6. **Updates**: Keep dependencies updated for security patches

### Production Docker Compose

For production, update `docker-compose.yml`:

```yaml
services:
  app:
    restart: always
    environment:
      - DEBUG=false
    # Remove volume mounts for code
```

## Development

### Running Locally (Without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up local PostgreSQL and update .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Running Tests

```bash
# With Docker
docker-compose exec app pytest

# Locally
pytest tests/ -v
```

### Project Structure

```
student-data-risk-mapper/
├── app/
│   ├── auth/           # OIDC and session handling
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # FastAPI route handlers
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic (scoring, exports)
│   ├── static/         # CSS, JavaScript
│   └── templates/      # Jinja2 templates
├── alembic/            # Database migrations
├── tests/              # Unit tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Risk Scoring

The risk score (0-100) is computed from five categories:

| Category | Max Points | Description |
|----------|------------|-------------|
| Data Sensitivity | 30 | Based on data types collected (IEP/health data scores highest) |
| Exposure Risk | 25 | Third-party sharing, advertising use, AI training |
| Security Controls | 20 | SSO, MFA, encryption, audit logs |
| Vendor Posture | 15 | Retention policy, deletion process |
| Integration Risk | 10 | API keys, real-time sync, SIS writeback |

**Risk Tiers:**
- **Low** (0-25): Well-configured with limited sensitive data
- **Moderate** (26-50): Some concerns to address
- **High** (51-75): Significant privacy risks requiring attention
- **Critical** (76-100): Immediate action recommended

**Unknown Penalty**: Selecting "Unknown" for any field adds points to reflect uncertainty. This encourages verification.

## User Roles

| Role | Capabilities |
|------|--------------|
| User | View, create, and assess systems |
| Auditor | User + read-only access to all systems |
| Admin | Full access including CSV export and future admin features |

Roles are assigned via Entra group membership. Without group claims, all users default to the basic "user" role.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard |
| `/systems/new` | GET/POST | Create system |
| `/systems/{id}` | GET | System detail |
| `/systems/{id}/edit` | GET/POST | Edit system |
| `/assessments/wizard/{id}` | GET | Assessment wizard |
| `/heatmap` | GET | Sensitive data heatmap |
| `/high-risk` | GET | High/critical systems list |
| `/exports/pdf/{id}` | GET | Download system PDF |
| `/exports/csv` | GET | Download inventory CSV (admin only) |
| `/auth/login` | GET | Initiate Entra login |
| `/auth/callback` | GET | OIDC callback |
| `/auth/logout` | GET | Sign out |
| `/health` | GET | Health check |

## License

Internal use only. Not for redistribution.

## Support

For issues, contact your district IT administrator.
