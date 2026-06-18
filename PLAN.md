# PLAN: Event-Driven Devin Automation for Apache Superset

## Objective

Build an event-driven automation that leverages the Devin API to remediate repository issues automatically.

The system should:

1. React to GitHub issue creation events.
2. Create and manage Devin sessions.
3. Track remediation progress.
4. Update GitHub with results.
5. Provide a lightweight dashboard that allows engineering leaders to monitor automation effectiveness.

---

# High-Level Architecture

```
                 GitHub
                    |
              Issue Created
                    |
                    v
              FastAPI Webhook
                    |
         Create Devin Session
                    |
         Store SQLite Record
                    |
             Return 200 OK
                    |
----------------------------------
                    |
           APScheduler Worker
                    |
         Every 30 seconds
                    |
        Query Running Sessions
                    |
          Check Devin Status
                    |
           +--------+--------+
           |                 |
        Running        Completed
           |                 |
        Nothing      Update GitHub
                     Update SQLite
                     Update Dashboard Data
```

---

# MVP Scope

## Event Source

Trigger:

* GitHub Issue Created webhook.

Supported issue types:

* Dependency upgrades.
* Security findings.
* Code quality improvements.
* Linting fixes.

Webhook endpoint:

```
POST /github/webhook
```

---

# FastAPI Service

## Receive GitHub Webhook

Validate:

* Event type.
* Shared secret.

Extract:

* Issue number.
* Title.
* Description.

---

## Create Devin Session

Construct a structured prompt including:

* Repository URL.
* Issue details.
* Expected remediation.
* Testing requirements.
* Pull request expectations.

Capture:

* Devin session ID.
* Session URL.
* Initial status.

---

## Persist Session

Store session details in SQLite.

Immediately return:

```
HTTP 200 OK
```

No long-running work should happen during webhook processing.

---

# SQLite Storage

SQLite acts as the central source of truth.

## Sessions Table

| Field            | Purpose             |
| ---------------- | ------------------- |
| id               | Internal ID         |
| github_issue     | GitHub issue number |
| devin_session_id | Devin session       |
| status           | Current state       |
| created_at       | Creation time       |
| updated_at       | Last update         |
| completed_at     | Completion time     |
| pr_url           | Pull request URL    |
| error_message    | Failure details     |
| acu              | ACU used            |

Session states:

```
NEW
RUNNING
COMPLETED
FAILED
```

---

# APScheduler Worker

Runs every:

```
30 seconds
```

Responsibilities:

## Query Active Sessions

Retrieve:

```
status = RUNNING
```

---

## Check Devin Status

### Running

Update last checked timestamp.

No additional action.

---

### Completed

Perform:

* Update SQLite.
* Store completion time.
* Record PR URL.
* Update GitHub issue.
* Update dashboard data.

---

### Failed

Record:

* Failure status.
* Error message.

Future enhancement:

* Retry policy.

---

# GitHub Updates

Upon successful remediation:

Post a comment:

```
Automation completed.

Devin Session:
...

Pull Request:
...

Summary:
...
```

Apply label:

```
automation-complete
```

Future enhancement:

* Automatically close issue after PR merge.

---

# Observability

The system provides built-in observability through API endpoints and a lightweight dashboard.

## Health Endpoint

```
GET /health
```

Returns:

```
{
    "status": "healthy"
}
```

---

## Status Endpoint

```
GET /status
```

Returns:

```
{
    "active": 3,
    "completed": 12,
    "failed": 1,
    "prs_created": 10
}
```

---

## Dashboard Endpoint

```
GET /dashboard
```

Provides a simple HTML dashboard summarizing automation activity.

Engineering leaders should immediately be able to answer:

* Is the automation running?
* How many tasks are active?
* How many tasks completed successfully?
* How many failed?
* How many pull requests were created?
* What is the average remediation time?

Example dashboard:

```
------------------------------------
 Devin Automation Dashboard
------------------------------------

Active Sessions:        3

Completed Sessions:    12

Failed Sessions:        1

PRs Created:           10

Success Rate:          92%

Average Fix Time:      14 min

Recent Activity:

Issue #42 -> Completed
Issue #43 -> Running
Issue #44 -> Failed

------------------------------------
```

Dashboard data is generated directly from SQLite.

No external monitoring infrastructure is required.

---

# Logging

Structured logs for operational visibility.

FastAPI:

```
Webhook received.
Session created.
Session stored.
```

Worker:

```
Polling session.
Session completed.
GitHub updated.
Dashboard updated.
```

Errors:

```
Session failed.
GitHub update failed.
API timeout.
```

---

# Repository Structure

```
app/
├── main.py
├── webhook.py
├── devin.py
├── github.py
├── worker.py
├── database.py
├── dashboard.py
├── models.py
└── config.py

templates/
└── dashboard.html

tests/
├── test_webhook.py
├── test_worker.py
├── test_dashboard.py
├── test_database.py

docker-compose.yml
requirements.txt
PLAN.md
```

---

# Docker Services

## API Service

Responsibilities:

* FastAPI.
* GitHub webhook.
* Devin session creation.
* Dashboard.
* Health endpoint.
* Status endpoint.

---

## Worker Service

Responsibilities:

* APScheduler.
* Devin polling.
* GitHub updates.
* SQLite updates.

Both services share:

* SQLite database.
* Configuration.

---

# Configuration

Environment variables:

```
DEVIN_SERVICE_USER_TOKEN
DEVIN_ORG_ID

GITHUB_TOKEN
GITHUB_WEBHOOK_SECRET

DATABASE_URL

POLL_INTERVAL=30
```

---

# Testing Strategy

## Unit Tests

Validate:

* Webhook parsing.
* Devin prompt generation.
* Database operations.
* Dashboard calculations.
* Session state transitions.

---

## Integration Tests

Simulate:

GitHub Issue →

Webhook →

Create Devin Session →

Store Session →

Worker Poll →

Completed →

GitHub Update →

Dashboard Update.

---

## Manual Demonstration

1. Create GitHub issue.

2. GitHub sends webhook.

3. FastAPI creates Devin session.

4. Session stored in SQLite.

5. Worker polls Devin.

6. Devin completes remediation.

7. GitHub issue updated.

8. Pull request recorded.

9. Dashboard reflects updated status.

---

# Success Criteria

The implementation is successful when:

* GitHub issue creation automatically triggers automation.
* Devin sessions are created successfully.
* Session state is persisted.
* Worker monitors active sessions.
* Completed sessions update GitHub.
* Pull request information is recorded.
* Dashboard accurately reflects system activity.
* Health and status endpoints provide operational visibility.
* Logs provide sufficient debugging information.

---

# Future Enhancements

* Retry failed sessions.
* Support additional GitHub events.
* Session prioritization.
* Multiple worker processes.
* PostgreSQL backend.
* Authentication for dashboard access.
* Automatic issue closure after PR merge.
* Batch remediation jobs.
* Slack or Teams notifications.
