# Strategy Warehouse Autonomous Marketing Engine

## Overview
The Strategy Warehouse Autonomous Marketing Engine is a high-performance system designed to automate the generation, scheduling, and publishing of trading strategy insights across multiple social media platforms. It integrates real-time trading data with automated content creation and engagement tracking.

## Quick Start (< 5 minutes)
1. Run `setup.bat` on Windows or `./setup.sh` on macOS/Linux.
2. Local setup creates `.env`, installs dependencies, and initializes `./data/marketing_engine.db` with schema, views, and seed data.
3. Start the backend from `solution/backend` with `uvicorn src.main:app --reload`.
4. Start the frontend from `solution/frontend` with `npm run dev`.

## Installation & Setup

### Prerequisites
- Node.js (v18+) or Python (3.10+)
- Docker Desktop if you want the full Postgres/Redis stack via compose

### Step-by-Step Installation
1. Local development uses SQLite by default through `DATABASE_URL=sqlite:///./data/marketing_engine.db`.
2. `python -m src.scripts.init_database` is the canonical bootstrap entry point. It is invoked by setup, backend startup, and Docker.
3. Docker Compose overrides `DATABASE_URL` to Postgres and mounts [`schema.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/schema.sql) and [`seed.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/seed.sql) into `/docker-entrypoint-initdb.d`.
4. Ensure `DATA_SOURCE_PATH` points to the correct Strategy Warehouse JSON directory.

## Configuration Reference
Refer to `.env.example` for a full list of required environment variables. Key sections include:
- **Connectors**: API credentials for Twitter, Discord, Telegram, etc.
- **Infrastructure**: Database and Redis URLs.
- **Settings**: Local paths and landing page configuration.

## API Outline
- `GET /health`: System health check.
- `POST /content/generate`: Trigger manual content generation.
- `GET /queue`: View scheduled posts.

## Deployment
This application can be deployed using Docker or directly on a VPS. Ensure all environment variables are properly set in your production environment.

## Database Assets
- Canonical SQL schema: [`schema.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/schema.sql)
- Canonical SQL seed data: [`seed.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/seed.sql)
- Migration bootstrap wrappers: [`0001_initial_schema.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/migrations/0001_initial_schema.sql), [`0002_seed_reference_data.sql`](/C:/Users/edebe/eds/ep_strategy_warehouse_marketing/schema/migrations/0002_seed_reference_data.sql)
