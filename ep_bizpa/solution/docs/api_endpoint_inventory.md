# API Endpoint Inventory [V20260217_2345]

## 1. Authentication & Session
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| POST | `/api/v1/auth/login` | Exchange credentials for JWT. | Public |
| POST | `/api/v1/auth/refresh` | Renew session token. | `user:read` |
| GET | `/api/v1/user/profile` | Get current user and team info. | `user:read` |

## 2. Capture & Items
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| POST | `/api/v1/capture/items` | Bulk upload items (offline queue sync). | `item:write` |
| GET | `/api/v1/items` | List items with filters and pagination. | `item:read` |
| GET | `/api/v1/items/{id}` | Get single item details. | `item:read` |
| PATCH | `/api/v1/items/{id}` | Update item (labels, status, link). | `item:write` |
| DELETE | `/api/v1/items/{id}` | Soft-delete/Archive item. | `item:write` |

## 3. Clients & Jobs
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| GET | `/api/v1/clients` | List all clients. | `client:read` |
| POST | `/api/v1/clients` | Create new client. | `client:write` |
| GET | `/api/v1/jobs` | List jobs with status filters. | `job:read` |
| PATCH | `/api/v1/jobs/{id}` | Update job status or due date. | `job:write` |

## 4. Search & Voice
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| POST | `/api/v1/search` | Execute FTS + filter query. | `item:read` |
| POST | `/api/v1/voice/process` | Submit audio for server-side ASR/NLU. | `voice:process` |

## 5. Sync (Delta Sync Protocol)
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| GET | `/api/v1/sync/delta` | Fetch all changes since `sync_token`. | `sync:pull` |
| POST | `/api/v1/sync/push` | Push local audit log of changes. | `sync:push` |

## 6. Plugin Specific
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| GET | `/api/v1/revenue/followups` | Get prioritized outreach list. | `revenue:read` |
| POST | `/api/v1/revenue/send` | Trigger outreach via template. | `revenue:write` |
| GET | `/api/v1/calendar` | Get events for range. | `calendar:read` |
| GET | `/api/v1/diary` | Get diary entries for date. | `diary:read` |

## 7. Inbox & Readiness
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| GET | `/api/v1/inbox` | List blocking inbox transactions requiring triage. | `item:read` |
| GET | `/api/v1/inbox/finish-now` | Shortcut queue for blocking transaction triage. | `item:read` |
| GET | `/api/v1/inbox/readiness` | Return the enforced active-quarter readiness report, issue summary, actionable issue list, and navigation targets. Supports `as_of_date`; ignores historical requested periods for drill-down purposes. | `item:read` |
| PATCH | `/api/v1/inbox/{id}/classification` | Apply category/business-personal/split classification fixes to a transaction. | `item:write` |
| POST | `/api/v1/inbox/{id}/duplicate-resolution` | Dismiss or merge a duplicate-flagged transaction. | `item:write` |
| POST | `/api/v1/inbox/undo-last` | Undo the latest inbox classification action. | `item:write` |

## 8. Exports
| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| POST | `/api/v1/export/generate` | Request CSV/Zip bundle. | `export:generate` |
| GET | `/api/v1/export/download/{id}` | Retrieve generated bundle. | `export:read` |
