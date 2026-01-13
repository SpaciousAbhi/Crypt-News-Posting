# Part 9: Security, Reliability, & Observability Plan

This document outlines the strategies and systems for ensuring the bot is secure, reliable in the face of errors, and transparent in its operations.

## 1. Security

Security is a foundational aspect of the bot's design, focusing on protecting user data, controlling access, and preventing abuse.

### Role-Based Access Control (RBAC)

A simple but effective RBAC system will be implemented to protect sensitive commands.

-   **Roles:**
    -   `owner`: The highest level of access. The Owner is defined by the `OWNER_TELEGRAM_ID` environment variable. There is only one owner.
    -   `admin`: Can manage tasks and view system status. Can be promoted by the owner.
    -   `user`: The default role. Can create and manage their own tasks.

-   **Permission Mapping:**
    -   `/status`, `/logs`, `/config_sync`: `owner` only.
    -   `/task_delete <someone_elses_task>`: `owner` only.
    -   Promoting users to `admin`: `owner` only.
    -   All other commands are accessible based on task ownership.

### Protection Against Abuse

-   **Rate Limiting:**
    -   **Global:** The bot will have a global rate limit to prevent it from being overwhelmed by a single user. (e.g., 30 commands per minute per user).
    -   **Task-Level:** Each task can have an optional `rate_limit_rpm` (requests per minute) defined. If a source chat produces messages faster than this limit, excess messages will be acknowledged but silently dropped to avoid spamming the target.

-   **Forward Loop Prevention:**
    -   A forward loop occurs when a bot's target chat is also another task's source chat, creating an infinite cycle.
    -   **Prevention:** During the task validation step (before enabling), the bot will check if any of the proposed target chat IDs are already being used as a source in another active task. If a potential loop is detected, the task will not be enabled, and the user will be warned.

### Secure Configuration

-   All sensitive information (API keys, bot tokens, database URLs) **must** be managed via Heroku environment variables. They will never be hardcoded in the source code or committed to version control.

## 2. Reliability

The bot is designed to be fault-tolerant and to maintain data integrity, even during restarts or failures.

### Message Deduplication

-   **Mechanism:** The `processed_messages` table is the core of the reliability strategy.
-   **Workflow:**
    1.  When a message is received, a unique `message_key` (`{source_chat_id}:{source_message_id}`) is generated.
    2.  The bot attempts to `INSERT` this key into the `processed_messages` table.
    3.  If the insert succeeds, the bot proceeds with processing.
    4.  If the insert fails due to a primary key constraint violation, it means the message has already been processed (or is currently being processed by a parallel dyno). The message is immediately and safely ignored.
-   **Impact:** This prevents any duplicate messages from being forwarded, even if the bot restarts mid-process.

### Graceful Shutdown

-   As detailed in the Heroku deployment plan, the bot's `main.py` includes signal handlers for `SIGTERM` and `SIGINT`.
-   When Heroku stops a dyno, the signal is caught, and a shutdown sequence is initiated. This sequence stops the Telegram clients from fetching new updates, waits for in-progress jobs to finish, and closes database connections cleanly.

### AI API Failure Handling

-   If the external AI API (e.g., Groq) fails or times out:
    -   The error will be caught immediately.
    -   A detailed error will be logged to the observability system.
    -   An alert will be sent to the `ADMIN_CHAT_ID` with the task name and the specific error.
    -   The message will **not** be forwarded. The bot will not forward a partially processed or untransformed message unless explicitly configured to do so (a potential future feature, e.g., "forward on failure").

## 3. Observability

Observability is key to understanding the bot's health and diagnosing issues in a production environment.

### Structured Logging

-   **Format:** All log output will be in a structured format (e.g., JSON), which is easily parsed by log management services like Heroku's own log drain or external tools (Datadog, Papertrail).
-   **Context:** Every log entry will contain important context, such as `task_id`, `source_chat_id`, and `target_chat_id`, allowing for easy filtering and debugging of specific tasks.
-   **Example Log Entry:**
    ```json
    {
      "timestamp": "2023-10-27T10:30:03Z",
      "level": "INFO",
      "message": "Forward successful.",
      "task_id": "task_crypto_news_main",
      "source_chat_id": -1001234567890,
      "target_chat_id": -1009876543210,
      "source_message_id": 12345
    }
    ```

### Task-Level Metrics (Future Extension)

While not in the initial build, the system is designed to support metrics. This could involve using a library like `prometheus_client` to track:
-   `messages_processed_total` (counter, with a `task_id` label)
-   `messages_forwarded_total` (counter, with `task_id` and `target_id` labels)
-   `ai_api_call_duration_seconds` (histogram, with `rule_type` label)
-   `api_errors_total` (counter, with `error_type` label)

These metrics can be exposed on a `/metrics` endpoint if a `web` dyno is added, or pushed to a service like StatsD.

### Admin Alerts

The `ADMIN_CHAT_ID` is a critical component of the observability strategy. Alerts are sent directly to the administrator via Telegram for high-priority events.

-   **Alert Triggers:**
    -   Any unhandled exception in the main application loop.
    -   Failure to communicate with the Telegram API.
    -   Failure to communicate with the AI API.
    -   A task being automatically disabled due to repeated permission errors.
    -   Successful completion of a `/config_sync` operation.

-   **Alert Format:**
    > **🔴 CRITICAL ERROR**
    > **Task:** `task_market_analysis_group`
    > **Error:** AI API call failed.
    > **Reason:** `APIConnectionError: Could not connect to Groq API.`
    >
    > This task will continue to retry, but operator attention is required.
