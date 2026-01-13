# Part 2: Data Models & Persistence Strategy

This document defines the complete database schema for the Advanced AI Forwarding Bot. The schema is designed to be robust, scalable, and normalized to ensure data integrity.

## 1. Database Choice

-   **Database:** PostgreSQL
-   **ORM:** SQLAlchemy
-   **Rationale:** As outlined in the architecture, PostgreSQL provides the reliability and advanced features needed for a production application. SQLAlchemy offers a powerful and maintainable way to interact with the database from Python.

## 2. Schema Diagram (Textual Representation)

The following diagram illustrates the relationships between the core tables in the database.

```
+-------------+      +----------------+      +-------------+
|    Users    |      |      Tasks     |      |  AI_Rules   |
|-------------|      |----------------|      |-------------|
| user_id (PK)|<--+--| task_id (PK)   |----->| rule_id (PK)|
| telegram_id |   |  | user_id (FK)   |      | task_id (FK)|
| role        |   |  | name           |      | rule_type   |
| created_at  |   |  | enabled        |      | config (JSON)|
+-------------+   |  | priority       |      | version     |
                  |  | rate_limit_rpm |      +-------------+
                  |  | created_at     |
                  |  +----------------+
                  |
                  +-----------------------+
                  |                       |
        +----------------+      +----------------+
        |     Sources    |      |     Targets    |
        |----------------|      |----------------|
        | source_id (PK) |      | target_id (PK) |
        | task_id (FK)   |      | task_id (FK)   |
        | chat_id        |      | chat_id        |
        | chat_type      |      | chat_type      |
        +----------------+      +----------------+

+------------------------+
|   Processed_Messages   |
|------------------------|
| message_key (PK)       |
| source_chat_id         |
| source_message_id      |
| expires_at             |
+------------------------+
```

## 3. Table Definitions

### `users`

Stores information about the Telegram users who can interact with the bot.

-   **Purpose:** Manages user identity and permissions (Role-Based Access Control).
-   **Columns:**
    -   `user_id` (Integer, Primary Key): Unique identifier for the user.
    -   `telegram_id` (BigInt, Unique, Not Null): The user's unique Telegram ID.
    -   `role` (String, Not Null, Default: 'user'): The user's role. Can be `user`, `admin`, or `owner`.
    -   `created_at` (DateTime, Not Null): Timestamp of when the user was first seen.

### `tasks`

The central table representing a single forwarding task.

-   **Purpose:** Defines a complete forwarding job, linking sources, targets, and AI rules.
-   **Columns:**
    -   `task_id` (Integer, Primary Key): Unique identifier for the task.
    -   `user_id` (Integer, Foreign Key -> `users.user_id`): The user who owns this task.
    -   `name` (String, Not Null): A human-readable name for the task (e.g., "Crypto News to Main Channel").
    -   `enabled` (Boolean, Not Null, Default: `False`): A toggle to quickly enable or disable the task.
    -   `priority` (Integer, Not Null, Default: 10): A priority level for the task. Lower numbers are higher priority (not used initially, but designed for future queuing systems).
    -   `rate_limit_rpm` (Integer, Nullable): The maximum number of messages to process per minute for this task. If `NULL`, no limit applies.
    -   `created_at` (DateTime, Not Null): Timestamp of when the task was created.

### `sources`

Represents a source chat for a specific task. A task can have multiple sources.

-   **Purpose:** Defines where the bot should listen for new messages.
-   **Columns:**
    -   `source_id` (Integer, Primary Key): Unique identifier for the source entry.
    -   `task_id` (Integer, Foreign Key -> `tasks.task_id`): The task this source belongs to.
    -   `chat_id` (BigInt, Not Null): The Telegram chat ID of the source channel or group. Can be a positive or negative number.
    -   `chat_type` (String, Not Null): The type of chat. Can be `public_channel`, `private_channel`, `public_group`, `private_group`.

### `targets`

Represents a target chat for a specific task. A task can have multiple targets.

-   **Purpose:** Defines where the bot should send the processed messages.
-   **Columns:**
    -   `target_id` (Integer, Primary Key): Unique identifier for the target entry.
    -   `task_id` (Integer, Foreign Key -> `tasks.task_id`): The task this target belongs to.
    -   `chat_id` (BigInt, Not Null): The Telegram chat ID of the target channel or group.
    -   `chat_type` (String, Not Null): The type of chat. Can be `public_channel`, `private_channel`, `group`.

### `ai_rules`

Stores the AI transformation rules for a specific task. A task can have multiple rules.

-   **Purpose:** Defines how a message should be modified by the AI engine.
-   **Columns:**
    -   `rule_id` (Integer, Primary Key): Unique identifier for the rule.
    -   `task_id` (Integer, Foreign Key -> `tasks.task_id`): The task this rule applies to.
    -   `rule_type` (String, Not Null): The type of AI transformation. Examples: `reword`, `summarize`, `add_header`, `add_footer`, `replace_watermark`, `translate`.
    -   `config` (JSONB, Not Null): A JSON object containing the specific parameters for the rule.
        -   *Example for `summarize`:* `{"format": "bullet", "length": "medium"}`
        -   *Example for `translate`:* `{"target_language": "Spanish"}`
    -   `version` (String, Not Null, Default: '1.0'): The version of the prompt used for this rule, to ensure deterministic behavior.

### `processed_messages`

A cache to prevent the bot from processing the same message twice, especially after a restart.

-   **Purpose:** Ensures exactly-once processing for each message. This is critical for reliability.
-   **Columns:**
    -   `message_key` (String, Primary Key): A unique composite key. Recommended format: `{source_chat_id}:{source_message_id}`.
    -   `source_chat_id` (BigInt, Not Null): The chat ID where the message originated.
    -   `source_message_id` (BigInt, Not Null): The message ID in the source chat.
    -   `expires_at` (DateTime, Not Null): A timestamp indicating when this record can be safely deleted. This prevents the table from growing indefinitely. A TTL (Time-To-Live) of 72 hours is recommended.

## 4. Data Integrity and Relationships

-   **One-to-Many:**
    -   A `User` can have many `Tasks`.
    -   A `Task` can have many `Sources`, `Targets`, and `AI_Rules`.
-   **Cascading Deletes:** To maintain data integrity, a cascading delete strategy will be implemented.
    -   If a `User` is deleted, all their associated `Tasks` (and by extension, the sources, targets, and rules for those tasks) will also be deleted.
    -   If a `Task` is deleted, all its associated `Sources`, `Targets`, and `AI_Rules` will be deleted.

## 5. Persistence Strategy for Heroku

-   **State:** All application state (tasks, users, etc.) is stored in the Heroku Postgres database. The bot's worker dynos are completely stateless.
-   **Ephemeral Filesystem:** The bot is designed to not rely on the local filesystem for any persistent data, making it fully compatible with Heroku's ephemeral filesystem.
-   **Message Deduplication:** The `processed_messages` table is the key to preventing message duplication after Heroku's automatic restarts. Before processing any message, the bot will first check if a `message_key` for it already exists in the table. If it does, the message is ignored. If not, the key is inserted before processing begins.
-   **Data Cleanup:** A periodic background job or a scheduled Heroku task will be responsible for cleaning up expired records from the `processed_messages` table to manage its size.
