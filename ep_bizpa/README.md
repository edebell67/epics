# BizPA - Business Personal Assistant

A voice-first business assistant API for capturing, organizing, and managing business activities.

## Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```cmd
setup.bat
```

**Unix/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2: Docker

```bash
docker-compose up -d
```

### Option 3: Manual Setup

1. Install dependencies:
```bash
cd solution/backend
npm install
```

2. Create environment file:
```bash
cp ../../.env.example .env
# Edit .env with your settings
```

3. Set up PostgreSQL database:
```bash
# Create database
psql -U postgres -c "CREATE DATABASE bizpa;"

# Apply schema
psql -U postgres -d bizpa -f src/models/schema.sql

# Apply migrations
psql -U postgres -d bizpa -f src/models/sync_migration.sql
psql -U postgres -d bizpa -f src/models/business_event_log_migration.sql
# ... apply other migrations as needed
```

4. Start the server:
```bash
npm start
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `5055` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `bizpa` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `SUPABASE_URL` | Supabase URL (optional) | `http://localhost:54321` |
| `SUPABASE_ANON_KEY` | Supabase anon key | - |
| `SUPABASE_SERVICE_KEY` | Supabase service key | - |
| `JWT_SECRET` | JWT signing secret | - |
| `DEBUG_SQL` | Log SQL queries | `false` |

## API Endpoints

Base URL: `http://127.0.0.1:5055/api/v1`

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1` | API info and endpoint list |

### Resources

| Resource | Endpoint | Description |
|----------|----------|-------------|
| Actions | `/api/v1/actions` | Task and action management |
| Auth | `/api/v1/auth` | Authentication |
| Business Events | `/api/v1/business-events` | Business event logging |
| Calendar | `/api/v1/calendar` | Calendar events |
| Clients | `/api/v1/clients` | Client management |
| Diary | `/api/v1/diary` | Diary entries |
| Evidence | `/api/v1/evidence` | Evidence/attachment management |
| Export | `/api/v1/export` | Data export (CSV, PDF, etc.) |
| Inbox | `/api/v1/inbox` | Inbox items and capture |
| Insights | `/api/v1/insights` | Business insights |
| Items | `/api/v1/items` | Generic item CRUD |
| Jobs | `/api/v1/jobs` | Job/project management |
| Notifications | `/api/v1/notifications` | Notification management |
| Revenue | `/api/v1/revenue` | Revenue tracking |
| Search | `/api/v1/search` | Full-text search |
| Stats | `/api/v1/stats` | Statistics and analytics |
| Sync | `/api/v1/sync` | Data synchronization |
| Team | `/api/v1/team` | Team management |
| VAT | `/api/v1/vat` | VAT calculations |
| Voice | `/api/v1/voice` | Voice capture and processing |

## Database Schema

The database includes these main tables:

- `clients` - Client/customer records
- `jobs` - Jobs/projects linked to clients
- `capture_items` - Captured business items (voice, manual entry)
- `voice_events` - Voice capture events with transcription
- `audit_events` - Audit trail for all changes
- `calendar_events` - Calendar and scheduling
- `notifications` - User notifications
- `sync_events` - Synchronization tracking
- `business_event_log` - Business activity logging

See `solution/backend/src/models/schema.sql` for complete schema.

## Development

### Running Tests
```bash
cd solution/backend
npm test
```

### Verification Scripts
```bash
npm run verify:inbox-actions
npm run verify:voice-capture
npm run verify:notification-engine
npm run verify:export-compatibility
```

## Project Structure

```
ep_bizpa/
├── setup.bat              # Windows setup script
├── setup.sh               # Unix setup script
├── docker-compose.yml     # Docker configuration
├── .env.example           # Environment template
├── README.md              # This file
└── solution/
    └── backend/
        ├── package.json
        ├── Dockerfile
        └── src/
            ├── app.js           # Express entry point
            ├── config/          # Database and service config
            ├── middleware/      # Express middleware
            ├── models/          # SQL schemas and migrations
            ├── routes/          # API route handlers
            └── services/        # Business logic
```

## Health Check

Verify the server is running:

```bash
curl http://127.0.0.1:5055/health
```

Expected response:
```json
{"status": "ok", "timestamp": "2026-03-15T12:00:00.000Z"}
```

## License

ISC
