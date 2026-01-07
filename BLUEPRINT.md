# Blueprint: The World's Best Telegram AI Forwarding Bot

This document is the complete design, architecture, and operational guide for the Advanced AI Forwarding Bot. It serves as the definitive reference for developers, operators, and product owners.

## Table of Contents

1.  [High-Level Architecture & Technology Stack](#part-1-high-level-architecture--technology-stack)
2.  [Data Models & Persistence Strategy](#part-2-data-models--persistence-strategy)
3.  [Heroku Deployment & Infrastructure Blueprint](#part-3-heroku-deployment--infrastructure-blueprint)
4.  [Telegram Access & Permissions Deep Dive](#part-4-telegram-access--permissions-deep-dive)
5.  [Configuration System Design](#part-5-configuration-system-design)
6.  [AI Transformation Engine Design](#part-6-ai-transformation-engine-design)
7.  [Complete Bot Command Reference](#part-7-complete-bot-command-reference)
8.  [Inline Button UI & UX Flow Mapping](#part-8-inline-button-ui--ux-flow-mapping)
9.  [Security, Reliability, & Observability Plan](#part-9-security-reliability--observability-plan)

---
# Part 1: High-Level Architecture & Technology Stack

This document outlines the system architecture, modular breakdown, and technology stack for the Advanced AI Forwarding Bot.

## 1. Architectural Principles

The bot's design is guided by the following core principles to ensure it is robust, scalable, and maintainable for a production environment.

-   **Statelessness:** The core application logic is stateless. The bot's worker dynos can be restarted, scaled up, or scaled down by Heroku at any time without loss of data or service interruption. All state is externalized to the persistence layer (PostgreSQL).
-   **Modularity:** The system is divided into distinct, loosely coupled modules with well-defined responsibilities. This separation of concerns simplifies development, testing, and future maintenance.
-   **Scalability:** The architecture is designed to handle a high volume of messages and tasks. The stateless nature of the worker and the use of a robust database allow for horizontal scaling by simply increasing the number of Heroku dynos.
-   **Fault Tolerance:** The bot is designed to be resilient to failures. It includes mechanisms for graceful shutdowns, error handling, and automatic retries where appropriate. The use of a persistent message processing cache prevents message duplication after a crash or restart.
-   **Security by Design:** Security is a primary consideration. All sensitive data is handled through environment variables, and role-based access control (RBAC) will be implemented to protect administrative functions.

## 2. System Architecture (Textual Diagram)

The system is designed as a single Heroku `worker` process that runs an asynchronous application. It consists of several interconnected modules that handle different aspects of the bot's functionality.

```
[External: Telegram API] <--> [Telegram API Clients Module] <--> [Core Logic & Orchestration Module]
                                     ^                                    ^
                                     |                                    |
                                     v                                    v
[AI Transformation Engine Module] <--> [Data Persistence Module (PostgreSQL)] <--> [Configuration Module]
                                     ^                                    ^
                                     |                                    |
                                     v                                    v
                               [User Interface Module (Commands & Buttons)] <--> [Observability Module (Logging & Alerts)]
```

**Flow of Data:**

1.  A message is posted in a monitored Telegram chat.
2.  The **Telegram API Clients Module** (either `python-telegram-bot` or `Pyrogram`) receives the incoming message event.
3.  The client passes the message to the **Core Logic & Orchestration Module**.
4.  The Core queries the **Data Persistence Module** to find matching forwarding tasks.
5.  If a task matches, the Core checks the **Processed Messages Cache** (in the database) to prevent duplication.
6.  The Core sends the message content and task rules to the **AI Transformation Engine Module**.
7.  The AI Engine applies the required transformations and returns the modified content.
8.  The Core sends the final content back to the **Telegram API Clients Module**.
9.  The client forwards the message to the target chats.
10. The **Observability Module** logs the entire process and sends an admin alert upon success or failure.

## 3. Module Breakdown

-   **Telegram API Clients (`clients.py`):**
    -   **Responsibility:** Manages all direct communication with the Telegram API.
    -   **Components:**
        -   Initializes and manages the lifecycle of the `python-telegram-bot` (for UI and basic functions) and `Pyrogram` (for user-level access) clients.
        -   Contains all event handlers for incoming messages, commands, and button callbacks.
        -   Abstracts the sending and forwarding of messages, handling API-specific exceptions.

-   **Core Logic & Orchestration (`core.py`):**
    -   **Responsibility:** The central brain of the application. It orchestrates the entire message forwarding pipeline.
    -   **Components:**
        -   Receives raw message objects from the `clients` module.
        -   Fetches relevant tasks from the `persistence` module.
        -   Enforces business logic (e.g., task enabled/disabled, rate limiting).
        -   Coordinates between the `persistence`, `ai_engine`, and `clients` modules.

-   **Data Persistence (`database.py`, `models.py`):**
    -   **Responsibility:** Manages all interactions with the PostgreSQL database.
    -   **Components:**
        -   Defines the SQLAlchemy data models for all tables (e.g., `Tasks`, `Users`, `Sources`).
        -   Handles database connections and session management.
        -   Provides CRUD (Create, Read, Update, Delete) operations for all data models.
        -   Manages the `processed_messages` table for deduplication.

-   **AI Transformation Engine (`ai_engine.py`):**
    -   **Responsibility:** Handles all AI-powered message modifications.
    -   **Components:**
        -   Interfaces with the external AI API (e.g., Groq, OpenAI).
        -   Contains the logic for each transformation type (summarize, reword, etc.).
        -   Manages prompt templates and versioning.

-   **Configuration Module (`config.py`, `config.yaml`):**
    -   **Responsibility:** Manages application configuration.
    -   **Components:**
        -   Loads environment variables and validates them.
        -   (Optional) Provides functions to parse the `config.yaml` and synchronize it with the database.

-   **User Interface (`ui/`):**
    -   **Responsibility:** Defines all user-facing interactions.
    -   **Components:**
        -   `commands.py`: Contains the logic for all slash commands (`/start`, `/task_create`).
        -   `buttons.py`: Defines all inline keyboard layouts and their callback logic.
        -   `text.py`: A centralized store for all UX copy and static text strings, enabling easy updates.

-   **Observability (`observability.py`):**
    -   **Responsibility:** Manages logging, metrics, and alerting.
    -   **Components:**
        -   Configures structured logging for the application.
        -   Provides functions for sending alerts to the admin chat via Telegram.
        -   (Future) Can be extended to integrate with external monitoring services.

## 4. Technology Stack

-   **Language:** **Python 3.10+**
    -   **Justification:** Python has a mature and extensive ecosystem for both web services and AI. Its asynchronous capabilities (`asyncio`) are essential for building a high-performance bot that can handle many concurrent operations.

-   **Primary Telegram Framework:** **`python-telegram-bot` (PTB)**
    -   **Justification:** PTB is a robust, well-maintained library with excellent features for building complex bot interactions, including a powerful `ConversationHandler` for guided UI flows and a clean object model. It is ideal for the command and button-based user interface.

-   **Secondary Telegram Framework:** **`Pyrogram`**
    -   **Justification:** Pyrogram excels at acting as a "user account" client via a session string. This is a critical requirement for accessing private channels or groups where a bot account cannot be added. Running it alongside PTB provides the "best of both worlds": a great UI framework and a powerful access client.

-   **Database:** **PostgreSQL**
    -   **Justification:** PostgreSQL is a production-grade, open-source relational database. It is fully supported by Heroku and provides the reliability, scalability, and data integrity required for this application. Its `JSONB` support is also highly valuable for storing flexible data like AI rule configurations.

-   **ORM:** **SQLAlchemy**
    -   **Justification:** SQLAlchemy is the de-facto standard Object-Relational Mapper for Python. It provides a powerful and flexible way to interact with the PostgreSQL database, abstracting away raw SQL queries and making the data access layer more maintainable and secure.

-   **Deployment Platform:** **Heroku**
    -   **Justification:** As mandated by the prompt, Heroku is a mature Platform-as-a-Service (PaaS) that simplifies deployment and management. Its support for environment variables, `Procfile`-based processes, and managed PostgreSQL makes it a perfect fit for this project.
---
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
---
# Part 3: Heroku Deployment & Infrastructure Blueprint

This document provides a comprehensive guide to deploying, configuring, and managing the Advanced AI Forwarding Bot on the Heroku platform.

## 1. Heroku Application Setup

The bot is designed to run as a single `worker` dyno on Heroku. It does not require a `web` dyno as it does not serve HTTP requests.

### Procfile

The `Procfile` is the entry point for the application and is placed in the root of the repository. It defines the command that Heroku will run to start the bot.

```Procfile
worker: python main.py
```

### runtime.txt

To ensure a consistent environment, the exact Python version is specified in `runtime.txt`.

```runtime.txt
python-3.10.14
```

### Dependencies

All Python dependencies are listed in `requirements.txt`. These will be installed automatically by Heroku during the build process.

## 2. Environment Variables

All configuration and secrets are managed via Heroku's Config Vars. This is a critical security practice and allows for easy configuration changes without modifying the code.

| Variable Name               | Required | Description                                                                                             | Example Value                                |
| --------------------------- | -------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`        | **Yes**  | The token for your Telegram bot, obtained from BotFather.                                               | `123456:ABC-DEF1234567890`                     |
| `DATABASE_URL`              | **Yes**  | The connection string for the Heroku Postgres database. This is **provisioned automatically** by Heroku.  | `postgres://user:pass@host:port/dbname`      |
| `ADMIN_CHAT_ID`             | **Yes**  | The Telegram chat ID of the administrator who will receive error notifications and alerts.                | `987654321`                                  |
| `GROQ_API_KEY`              | **Yes**  | The API key for the Groq AI service used for message transformations.                                   | `gsk_aBcDeFgHiJkLmNoPqRsTuVwXyZ`               |
| `API_ID`                    | Optional | The `api_id` for a Telegram user account, used for Pyrogram. Required for user-level access.          | `1234567`                                    |
| `API_HASH`                  | Optional | The `api_hash` for a Telegram user account, used for Pyrogram. Required for user-level access.          | `0123456789abcdef0123456789abcdef`           |
| `PYROGRAM_SESSION_STRING`   | Optional | The session string for a Pyrogram user client. Required for user-level access.                          | `Ag...` (a very long string)                 |
| `LOG_LEVEL`                 | Optional | The logging level for the application.                                                                  | `INFO` (default), `DEBUG`                    |
| `OWNER_TELEGRAM_ID`         | **Yes**  | The Telegram ID of the bot's owner, who has the highest level of permissions.                             | `123456789`                                  |

## 3. Heroku Deployment Checklist

This checklist provides a step-by-step guide for a first-time deployment of the bot to Heroku.

**Prerequisites:**
- A Heroku account.
- The Heroku CLI installed and authenticated (`heroku login`).
- The project code pushed to a GitHub repository.

**Deployment Steps:**

1.  **Create Heroku App:**
    -   From your Heroku dashboard, click "New" -> "Create new app".
    -   Choose a unique app name and your preferred region.

2.  **Provision Database:**
    -   In the app's "Resources" tab, search for the **Heroku Postgres** add-on.
    -   Select the plan (the free "Hobby Dev" plan is suitable for initial testing).
    -   Click "Provision". Heroku will automatically create the database and add the `DATABASE_URL` config var.

3.  **Configure Environment Variables:**
    -   Go to the app's "Settings" tab and click "Reveal Config Vars".
    -   Add all the required environment variables from the table above (`TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID`, etc.).
    -   **Do not** add `DATABASE_URL`, as it is already set by the add-on.

4.  **Connect to GitHub and Deploy:**
    -   Go to the app's "Deploy" tab.
    -   Under "Deployment method," select "GitHub".
    -   Connect to your GitHub account and search for the bot's repository.
    -   Once connected, you can choose to enable "Automatic Deploys" (which will redeploy the app whenever you push to the `main` branch) or perform a manual deploy.
    -   For the first deployment, click **"Deploy Branch"** at the bottom of the page.

5.  **Initialize the Database:**
    -   After the first deployment, the database tables need to be created. Heroku's one-off dynos are used for this.
    -   Open your terminal and run the following command, replacing `<your-app-name>`:
        ```bash
        heroku run python -c "from database import init_db; init_db()" --app <your-app-name>
        ```
    -   This command runs the `init_db` function in a separate dyno, creating all the SQLAlchemy tables.

6.  **Enable the Worker Dyno:**
    -   By default, Heroku does not start any dynos.
    -   Go back to the "Resources" tab.
    -   You will see your `worker: python main.py` process listed. Click the "Edit" icon (a pencil).
    -   Toggle the switch to enable the dyno and click "Confirm".

7.  **Check the Logs:**
    -   The bot should now be running. You can monitor its startup and activity by running the following command in your terminal:
        ```bash
        heroku logs --tail --app <your-app-name>
        ```
    -   You should see the "Bot started. Listening for messages..." log entry.

## 4. Maintenance and Operations

-   **Restarting:** If the bot becomes unresponsive, you can restart it from the Heroku dashboard ("More" -> "Restart all dynos") or via the CLI:
    ```bash
    heroku restart --app <your-app-name>
    ```
-   **Graceful Shutdown:** The application code includes signal handlers for `SIGTERM` (which Heroku uses to stop dynos). This ensures a graceful shutdown, where the bot will stop listening for new messages and complete any in-progress work before exiting. This is critical for preventing data corruption and message duplication.
-   **Scaling:** If the bot needs to handle a very high volume of messages, you can scale it horizontally by increasing the number of worker dynos in the "Resources" tab. Since the application is stateless, multiple dynos can run in parallel without interfering with each other.
-   **Database Backups:** Heroku Postgres automatically creates backups. You can manage these backups and perform restores from the Heroku dashboard.
---
# Part 4: Telegram Access & Permissions Deep Dive

This document details the precise permissions the Advanced AI Forwarding Bot requires to function correctly. It also provides user-facing instructions for setup and outlines the bot's internal validation checks.

## 1. Required Permissions Matrix

For the bot to operate reliably, it needs specific administrative rights in the channels and groups it interacts with. The requirements vary depending on whether the chat is a source or a target.

| Chat Type               | Role in Source Chat                                    | Role in Target Chat                                     | Rationale                                                                                                                              |
| ----------------------- | ------------------------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Public Channel**      | N/A (Can read all public messages)                     | **Administrator** with `Post Messages` permission       | The bot needs admin rights to send the modified/forwarded message to the target channel.                                               |
| **Private Channel**     | **Administrator** with `Read Messages` permission      | **Administrator** with `Post Messages` permission       | Must be an admin to access the message stream of a private channel. Must be an admin to post in the target private channel.           |
| **Public Group**        | **Member** (Can read all public messages)              | **Member** with `Send Messages` permission              | Standard group permissions are sufficient for reading from a public group and posting to any group it is a member of.                  |
| **Private Group / Supergroup** | **Member**                                             | **Member** with `Send Messages` permission              | As a member, the bot can read all messages in a private group. Standard member permissions allow it to post in the target group. |

**Note on Pyrogram (User Account Mode):**
If the bot is configured with a Pyrogram session string, it acts as a regular user. In this mode:
-   It only needs to be a **member** of a source channel/group to read messages.
-   It only needs to be a **member** of a target channel/group with posting permissions to send messages.
-   This mode is essential for accessing chats where you cannot grant admin rights to a bot.

## 2. User-Facing Setup Instructions

The bot will provide these clear, step-by-step instructions within the `/help` command or a dedicated setup flow.

### How to Add the Bot to a Private Channel

> To use a private channel as a source or a target, you need to add me as an administrator.
>
> 1.  Open the private channel you want to use.
> 2.  Tap the channel's name at the top to open its profile.
> 3.  Go to **Administrators** -> **Add Admin**.
> 4.  Search for me (`@YourBotUsername`) and select me.
> 5.  **Important:**
>     -   For a **Source Channel**, please grant me the **"Read Messages"** permission.
>     -   For a **Target Channel**, please grant me the **"Post Messages"** permission.
> 6.  Tap the checkmark to save. You're all set!

### How to Add the Bot to a Private Group

> To use a private group or supergroup as a source or a target, you just need to add me as a member.
>
> 1.  Open the private group you want to use.
> 2.  Tap the group's name at the top to open its profile.
> 3.  Tap **"Add Members"**.
> 4.  Search for me (`@YourBotUsername`) and add me to the group.
> 5.  That's it! I'll be able to see new messages and post replies.

## 3. Pre-Task Validation Checks

To prevent tasks from failing silently, the bot will perform a series of validation checks **before a task can be enabled**. These checks are triggered when a user runs the `/task_enable <task_id>` command or uses the "Enable" button in the UI.

The validation logic is as follows:

1.  **Retrieve Task:** Fetch the task configuration, including all sources and targets, from the database.
2.  **Iterate Over Sources:**
    -   For each source `chat_id`:
        -   Attempt to get chat information using `bot.get_chat(chat_id)`. This verifies the bot has access.
        -   If it's a private channel, check the bot's status using `bot.get_chat_member(chat_id, bot.id)`. Verify that `status` is 'administrator'.
        -   If any check fails, store a specific error message.
3.  **Iterate Over Targets:**
    -   For each target `chat_id`:
        -   Attempt to get chat information.
        -   Check the bot's status in the chat. Verify it has the required permissions to post messages.
        -   To be certain, the bot can attempt to send and then immediately delete a test message like "Validating permissions...". This is the most reliable check.
        -   If any check fails, store a specific error message.
4.  **Report Results:**
    -   If all checks pass, the bot enables the task and sends a success message.
    -   If any check fails, the bot will **not** enable the task. Instead, it will reply with a detailed report of all the issues it found, with clear instructions on how to fix them.

## 4. User-Facing Error Messages

Clear and actionable error messages are crucial for a good user experience.

**Example: Permission Validation Failure Report**

> ⚠️ **Task "Crypto News" could not be enabled.**
>
> I checked the channels and groups for this task and found a few issues that need to be fixed first:
>
> **Source Chat: `-1001234567890`**
> -   **Error:** I can't seem to access this private channel. Please make sure I have been added as an administrator with the "Read Messages" permission.
>
> **Target Chat: `-1009876543210`**
> -   **Error:** I am a member of this channel, but I don't have permission to post messages. Please promote me to an Administrator with the "Post Messages" permission.
>
> Please resolve these issues and then try enabling the task again. You can find detailed instructions in the `/help` menu.

**Example: Error During a Running Task**

If a permission is revoked while a task is running, the bot will detect it on the next forwarding attempt.

> ❗️ **Task "Market Updates" has been automatically disabled.**
>
> I was unable to forward a message to the target channel "Main Updates" (`-1009876543210`).
>
> **Reason:** It seems my permission to post messages was removed.
>
> Please review the channel's settings and re-enable the task once the issue is resolved.
---
# Part 5: Configuration System Design

This document outlines the dual-mode configuration system for the Advanced AI Forwarding Bot, which combines the flexibility of a live UI with the robustness of a declarative `config.yaml` file.

## 1. Configuration Philosophy

The bot employs a hybrid configuration model to cater to different user needs:

1.  **Database as the Single Source of Truth:** For the live, running application, the **PostgreSQL database is the single source of truth**. All task creations, edits, and deletions performed via the Telegram UI directly modify the database. This ensures instant, atomic updates and is ideal for a stateless application architecture.

2.  **`config.yaml` for Declarative Management:** A `config.yaml` file provides a human-readable, version-controllable way to manage the bot's configuration. This file is **not** read by the bot on startup. Instead, it serves three primary purposes:
    *   **Initial Setup:** Quickly populating the bot with a predefined set of tasks.
    *   **Backup & Restore:** Providing a simple way to back up and restore the bot's entire configuration.
    *   **Bulk Edits:** Allowing advanced users to make complex changes in a text editor before applying them.

## 2. `config.yaml` Format

The `config.yaml` has a clear, declarative structure. It consists of a top-level `tasks` dictionary, where each key is a unique string identifier for the task.

```yaml
# config.yaml
#
# Declarative configuration for the Advanced AI Forwarding Bot.
# Use the /config_sync --import command to apply this configuration to the database.

tasks:
  # Unique identifier for the task.
  task_crypto_news_main:
    name: "Crypto News -> Main Channel"
    enabled: true
    # Optional: Rate limit in messages per minute.
    rate_limit_rpm: 60
    sources:
      # A list of source chat IDs.
      - -1001234567890  # e.g., Private News Channel
      - "binance_announcements" # Public channel username
    targets:
      # A list of target chat IDs.
      - -1009876543210  # e.g., Private Main Channel
    ai_rules:
      # A list of AI transformations, applied in order.
      - type: "replace_watermark"
        config:
          replace_from: "Join our VIP group"
          replace_to: "Forwarded by AI Bot"
        version: "1.0"

      - type: "summarize"
        config:
          format: "bullet"
          length: "medium"
        version: "1.1"

      - type: "add_footer"
        config:
          # You can use variables that will be populated by the bot.
          text: |
            ---
            Forwarded from: {source_chat_name}
            Posted at: {message_timestamp}
        version: "1.0"

  task_market_analysis_group:
    name: "Market Analysis -> Trading Group"
    enabled: false
    sources:
      - -1001111222333
    targets:
      - -100444555666
    ai_rules:
      - type: "translate"
        config:
          target_language: "English"
        version: "1.0"
```

## 3. Synchronization Strategy

Interaction between the `config.yaml` and the database is managed by a dedicated, owner-only command. This ensures that changes are deliberate and controlled.

### Command: `/config_sync`

-   **Permission:** `owner`
-   **Purpose:** Allows the bot owner to import a `config.yaml` file or export the current database configuration to a YAML file.

#### Import Flow: `/config_sync`

1.  **Owner sends the command:** `/config_sync`
2.  **Bot replies:**
    > "Please reply to this message with your `config.yaml` file to begin the import process.
    >
    > **Warning:** This will overwrite any tasks in the database that have the same name as tasks in your file. This action cannot be undone."
3.  **Owner replies with the `config.yaml` file.**
4.  **Bot performs a dry run:**
    -   The bot parses the YAML file and validates its structure.
    -   It compares the tasks in the file with the tasks in the database.
    -   **Bot replies with a summary:**
        > **Configuration Sync - Dry Run Summary**
        >
        > I have analyzed your `config.yaml` file. Here are the changes I will make:
        >
        > -   **Create:** 2 new tasks (`task_market_analysis_group`, `task_other_news`)
        > -   **Update:** 1 existing task (`task_crypto_news_main`)
        > -   **No Change:** 3 tasks
        > -   **Delete:** (This import will not delete any tasks not present in the file.)
        >
        > Do you want to apply these changes?
        >
        > [✅ Apply Changes] [❌ Cancel]
5.  **Owner confirms:** Clicks "✅ Apply Changes".
6.  **Bot executes the changes:**
    -   The bot iterates through the tasks in the YAML file.
    -   For each task, it performs an "upsert" operation: if a task with the same `name` already exists in the database, it's updated; otherwise, a new task is created.
    -   After the operation, the bot's in-memory task cache is reloaded.
7.  **Bot confirms completion:**
    > "✅ Configuration sync complete. 2 tasks created, 1 task updated."

## 4. Hot-Reloading

True hot-reloading (where the bot automatically detects changes to a file on the filesystem) is not implemented by design. It is not a good fit for the Heroku ephemeral filesystem and can lead to unpredictable behavior.

The `/config_sync` command provides a **safe, explicit, and user-initiated** alternative that achieves the same goal: applying configuration changes from a file without needing to restart the bot. This approach is more robust and suitable for a production environment.
---
# Part 6: AI Transformation Engine Design

This document details the architecture and functionality of the AI Transformation Engine, the core component responsible for all intelligent message modifications.

## 1. Engine Overview

The AI Transformation Engine is a modular component that receives raw message content and a set of rules, then applies those rules sequentially to produce the final, modified output.

-   **Sequential Processing:** AI rules defined for a task are applied in the order they are listed. The output of one rule becomes the input for the next.
-   **AI Provider:** The engine is designed to interface with a powerful Large Language Model (LLM) via an API. The primary choice is the **Groq API** for its high speed, but it can be adapted to other providers like OpenAI or Anthropic.
-   **Deterministic Behavior:** The engine uses a "prompt versioning" system. Each AI rule is tied to a specific version of a prompt template. This ensures that even if prompts are improved in the future, existing tasks will continue to behave predictably until they are explicitly upgraded.

## 2. AI Rule Definitions

Below are the specifications for each supported AI rule type.

### a) `reword`

-   **Purpose:** Rephrases the entire message to match a specific tone or style, without losing the original meaning.
-   **Config (`JSONB`):**
    ```json
    {
      "tone": "string",
      "audience": "string"
    }
    ```
    -   `tone`: (Required) The desired tone. Examples: `Formal`, `Casual`, `Professional`, `Enthusiastic`, `Objective`.
    -   `audience`: (Required) The target audience. Examples: `General Public`, `Expert Traders`, `Beginners`, `Developers`.
-   **Prompt Version 1.0:**
    ```
    Rephrase the following text to have a {tone} tone, suitable for an audience of {audience}. Do not add any new information or commentary. Preserve the original meaning and any factual data, like numbers or links.

    Original text:
    """
    {message_text}
    """
    ```

### b) `summarize`

-   **Purpose:** Condenses a long message into a more concise format.
-   **Config (`JSONB`):**
    ```json
    {
      "format": "string",
      "length": "string"
    }
    ```
    -   `format`: (Required) The output format. Can be `paragraph`, `bullet_points`.
    -   `length`: (Required) The desired length of the summary. Can be `short` (1-2 sentences), `medium` (a short paragraph or 3-5 bullet points), `long` (a detailed summary).
-   **Prompt Version 1.0 (paragraph):**
    ```
    Summarize the key information in the following text into a {length} paragraph. Focus on the main conclusions and actionable insights.

    Original text:
    """
    {message_text}
    """
    ```
-   **Prompt Version 1.0 (bullet_points):**
    ```
    Summarize the key information in the following text into a list of {length} bullet points. Each bullet point should be concise and impactful.

    Original text:
    """
    {message_text}
    """
    ```

### c) `add_header` / `add_footer`

-   **Purpose:** Appends a static or dynamic piece of text to the beginning or end of the message. This rule is processed **locally** and does not require an AI API call.
-   **Config (`JSONB`):**
    ```json
    {
      "text": "string"
    }
    ```
    -   `text`: (Required) The text to add. It supports variables that the bot will replace.
-   **Supported Variables:**
    -   `{source_chat_name}`: The display name of the source channel/group.
    -   `{source_chat_id}`: The ID of the source chat.
    -   `{message_timestamp}`: The date and time the original message was posted.
    -   `{task_name}`: The name of the forwarding task.

### d) `replace_watermark`

-   **Purpose:** A simple, local find-and-replace operation. Useful for removing or replacing recurring text like advertisements or channel links. This rule is processed **locally**.
-   **Config (`JSONB`):**
    ```json
    {
      "replace_from": "string",
      "replace_to": "string"
    }
    ```
    -   `replace_from`: (Required) The exact text to find.
    -   `replace_to`: (Required) The text to replace it with. Can be an empty string (`""`) to simply remove the text.

### e) `translate`

-   **Purpose:** Translates the message text into a different language.
-   **Config (`JSONB`):**
    ```json
    {
      "target_language": "string"
    }
    ```
    -   `target_language`: (Required) The language to translate the text into (e.g., `Spanish`, `Japanese`, `German`).
-   **Prompt Version 1.0:**
    ```
    Translate the following text into {target_language}. Preserve the original formatting, such as line breaks and links, as much as possible.

    Original text:
    """
    {message_text}
    """
    ```

## 3. Data Flow within the Engine

The `AIEngine` will have a primary method, `transform(text, rules)`, which operates as follows:

```python
def transform(text: str, rules: list[AIRule]) -> str:
    current_text = text
    for rule in rules:
        if rule.type == "add_header":
            # Locally process header
            header = substitute_variables(rule.config["text"])
            current_text = f"{header}\n\n{current_text}"

        elif rule.type == "replace_watermark":
            # Locally process watermark
            current_text = current_text.replace(
                rule.config["replace_from"],
                rule.config["replace_to"]
            )

        elif rule.type in ["reword", "summarize", "translate"]:
            # Remotely process with AI
            prompt = get_prompt(rule.type, rule.version, rule.config)
            filled_prompt = prompt.format(
                message_text=current_text, **rule.config
            )
            current_text = ai_api_call(filled_prompt)

        elif rule.type == "add_footer":
            # Locally process footer
            footer = substitute_variables(rule.config["text"])
            current_text = f"{current_text}\n\n{footer}"

    return current_text
```

## 4. Prompt Versioning and Management

-   **Storage:** All prompt templates will be stored in a dedicated, non-executable file (e.g., `prompts.json`) within the application's codebase.
-   **Structure:**
    ```json
    {
      "summarize": {
        "1.0": {
          "paragraph": "Summarize the key information...",
          "bullet_points": "Summarize the key information..."
        },
        "1.1": {
          "paragraph": "An improved summary prompt...",
          "bullet_points": "An improved bullet point prompt..."
        }
      },
      "translate": {
        "1.0": "Translate the following text..."
      }
    }
    ```
-   **Upgrading:** When a user edits a task, the UI can show a notification if a newer prompt version is available for one of their rules, giving them the option to upgrade. This ensures a smooth and controlled evolution of the AI's capabilities.
---
# Part 7: Complete Bot Command Reference

This document provides a definitive reference for all slash commands available in the Advanced AI Forwarding Bot.

---

## 1. Global Commands

These commands are available to all users, though some may have permission restrictions.

### `/start`

-   **Permission:** `user`
-   **Purpose:** Initializes the bot for a new user, displays the welcome message, and shows the main menu.
-   **Success Response:**
    > 👋 **Welcome to the Advanced AI Forwarding Bot!**
    >
    > I can monitor Telegram chats, apply powerful AI transformations to messages, and forward them to your channels or groups.
    >
    > Please choose an option from the menu below to get started.
    >
    > **[View Tasks]** **[Create New Task]**
    > **[Help & Documentation]** **[Settings]**

### `/help`

-   **Permission:** `user`
-   **Purpose:** Displays a detailed help message explaining how the bot works, how to configure it, and how to get support.
-   **Success Response:**
    > ℹ️ **Help & Documentation**
    >
    > **How I Work**
    > This bot forwards messages from source chats to target chats, with optional AI modifications. A "Task" is a single forwarding rule that links sources, targets, and AI rules.
    >
    > **Accessing Private Chats**
    > For me to see messages in private chats, you must add me:
    > - **Private Channels:** Add me as an **Administrator** with "Read Messages" (for sources) or "Post Messages" (for targets) permissions.
    > - **Private Groups:** Simply add me as a **Member**.
    >
    > **Finding Chat IDs**
    > To get the ID of a private channel or group, forward a message from it to a bot like `@JsonDumpBot`. The `forward_from_chat` -> `id` field is the chat ID you need.
    >
    > Use the main menu to manage your tasks. If you need further assistance, please contact the bot owner.

### `/status`

-   **Permission:** `admin`
-   **Purpose:** Provides a real-time status of the bot's operations and health.
-   **Success Response:**
    > **Bot Status**
    >
    > - **Status:** `OPERATIONAL`
    > - **Active Tasks:** 8
    > - **Total Messages Forwarded (24h):** 1,423
    > - **Errors (24h):** 5
    > - **Uptime:** 3 days, 12 hours
    > - **Pyrogram Client:** `CONNECTED`
    >
    > All systems are running normally.

### `/tasks`

-   **Permission:** `user`
-   **Purpose:** Displays a list of all forwarding tasks owned by the user, including their status.
-   **Success Response:**
    > **Your Forwarding Tasks**
    >
    > Here is a list of your currently configured tasks. You can edit or delete them from this menu.
    >
    > - **(✅ Enabled)** Crypto News -> Main Channel
    >   `ID: task_crypto_news_main`
    >   **[Edit]** **[Disable]** **[Delete]**
    >
    > - **(❌ Disabled)** Market Analysis -> Trading Group
    >   `ID: task_market_analysis_group`
    >   **[Edit]** **[Enable]** **[Delete]**
    >
    > **[Create New Task]**

### `/logs`

-   **Permission:** `owner`
-   **Purpose:** Retrieves the most recent log entries for a specific task to help with debugging.
-   **Usage:** `/logs <task_id>`
-   **Success Response:**
    > **Logs for Task: `task_crypto_news_main`** (Last 10 entries)
    >
    > `[2023-10-27 10:30:01] INFO: Received message 123 from chat -1001234567890.`
    > `[2023-10-27 10:30:01] INFO: Matched task "Crypto News -> Main Channel".`
    > `[2023-10-27 10:30:02] INFO: Applying AI rule: summarize.`
    > `[2023-10-27 10:30:03] INFO: Forwarding to target -1009876543210.`
    > `[2023-10-27 10:30:03] INFO: Forward successful.`
-   **Error / Edge Case Responses:**
    -   (If task_id is missing) > "Usage: `/logs <task_id>`. Please provide the ID of the task you want to view."
    -   (If task_id is invalid) > "Error: Task with ID `invalid_id` not found."
    -   (If user is not owner) > "You do not have permission to use this command."

### `/settings`

-   **Permission:** `user`
-   **Purpose:** Allows users to view and manage their settings (this is a placeholder for future features like notification preferences).
-   **Success Response:**
    > **Settings**
    >
    > There are currently no user-specific settings to configure. This menu will be expanded in the future.
    >
    > **[⬅️ Back to Main Menu]**

### `/health`

-   **Permission:** `user`
-   **Purpose:** A simple command to check if the bot is online and responding.
-   **Success Response:**
    > "Pong! I am online and running."

---

## 2. Task Commands

These commands are used to manage the lifecycle of forwarding tasks.

### `/task_create`

-   **Permission:** `user`
-   **Purpose:** Initiates the interactive, button-based flow to create a new forwarding task.
-   **Success Response:**
    > **Create a New Task**
    >
    > Let's set up a new forwarding task. What would you like to name it? (e.g., "Crypto News to Main Channel")

### `/task_edit`

-   **Permission:** `user`
-   **Purpose:** Initiates the interactive flow to edit an existing task.
-   **Usage:** `/task_edit <task_id>` or via the `/tasks` menu.
-   **Success Response:**
    > **Editing Task: "Crypto News -> Main Channel"**
    >
    > What would you like to edit?
    >
    > **[Name]** **[Sources]** **[Targets]**
    > **[AI Rules]** **[⬅️ Back to Tasks]**
-   **Error / Edge Case Responses:**
    -   (If task_id is invalid or not owned by user) > "Error: Task not found or you do not have permission to edit it."

### `/task_delete`

-   **Permission:** `user`
--   **Purpose:** Deletes a forwarding task.
-   **Usage:** `/task_delete <task_id>` or via the `/tasks` menu.
-   **Success Response (Confirmation):**
    > **Are you sure?**
    >
    > This will permanently delete the task "Crypto News -> Main Channel". This action cannot be undone.
    >
    > **[⚠️ Yes, Delete Task]** **[❌ Cancel]**
-   **Success Response (Final):**
    > "✅ Task "Crypto News -> Main Channel" has been deleted."
-   **Error / Edge Case Responses:**
    -   (If task_id is invalid or not owned by user) > "Error: Task not found or you do not have permission to delete it."

### `/task_enable` / `/task_disable`

-   **Permission:** `user`
-   **Purpose:** Enables or disables a task.
-   **Usage:** `/task_enable <task_id>` or via the `/tasks` menu.
-   **Success Response (Enable):**
    > "Validating permissions... ✅ All checks passed. Task "Crypto News -> Main Channel" is now enabled and running."
-   **Success Response (Disable):**
    > "❌ Task "Crypto News -> Main Channel" has been disabled."
-   **Error / Edge Case Responses:**
    -   (On enable, if permissions fail) > "⚠️ **Task "Crypto News" could not be enabled.** I checked the channels and groups for this task and found a few issues..." (See Permissions doc for full text).
    -   (If task is already in the desired state) > "Task "Crypto News" is already enabled."

### `/task_test`

-   **Permission:** `user`
-   **Purpose:** Sends a test message through the task's pipeline to a specified target, allowing the user to preview the AI transformations.
-   **Usage:** `/task_test <task_id>`
-   **Success Response:**
    > **Test Task: "Crypto News -> Main Channel"**
    >
    > I will send a test message through this task's full AI pipeline. Where would you like the test output sent?
    >
    > **[Send to this Chat]** **[Send to Task Targets]** **[Cancel]**
-   **Error / Edge Case Responses:**
    -   (If task_id is invalid) > "Error: Task not found."
---
# Part 8: Inline Button UI & UX Flow Mapping

This document provides a detailed, step-by-step walkthrough of the key user-facing flows that rely on inline button interactions. A clear and intuitive UI is critical for making the bot's powerful features accessible.

## 1. Guiding Principles

-   **Conversational:** The UI should feel like a guided conversation, with the bot asking questions and the user providing answers through buttons or simple text replies.
-   **Stateful:** Each flow is managed by a `ConversationHandler` (or similar state machine), so the bot always knows where the user is in the process.
-   **Cancellable:** Every step of a multi-step process must have a "Cancel" or "Back" option, allowing the user to exit gracefully without being trapped.
-   **Clear Confirmations:** Every action (adding, deleting, saving) must be followed by a clear confirmation message.

## 2. Core User Flow: Creating a New Task

This is the most complex flow and serves as a template for other interactions like editing a task.

---

### **Step 1: Initiation**

The user either clicks the **[Create New Task]** button from the main menu or types `/task_create`.

> **Bot:**
> Let's set up a new forwarding task. What would you like to name it? (e.g., "Crypto News to Main Channel")

---

### **Step 2: Naming the Task**

The user replies with a text message containing the name.

> **User:**
> Crypto News Feed

> **Bot:**
> Great! Your task is named "Crypto News Feed".
>
> Now, let's configure the task. Use the buttons below. Your changes are saved as we go. When you're done, you can save the task.
>
> ---
> **Task: Crypto News Feed**
> - **Sources:** (none)
> - **Targets:** (none)
> - **AI Rules:** (none)
> ---
> **[Manage Sources]** **[Manage Targets]**
> **[Manage AI Rules]** **[Rename Task]**
> **[✅ Save & Enable]** **[💾 Save as Disabled]**
> **[❌ Cancel Creation]**

---

### **Step 3: Managing Sources**

The user clicks **[Manage Sources]**.

> **Bot:**
> **Manage Sources for "Crypto News Feed"**
>
> Currently, there are no source chats. A source is where I'll listen for new messages.
>
> **[➕ Add Source]**
> **[⬅️ Back to Task Menu]**

The user clicks **[➕ Add Source]**.

> **Bot:**
> Please send me the chat ID of the source channel or group.
>
> You can also send the public channel's username (e.g., `@channel_name`).
>
> (For help finding a chat ID, see `/help`.)

The user sends a chat ID.

> **User:**
> -1001234567890

> **Bot:**
> ✅ Source `-1001234567890` added.
>
> **Manage Sources for "Crypto News Feed"**
> - `-1001234567890` **[🗑️ Remove]**
>
> **[➕ Add Another Source]**
> **[⬅️ Back to Task Menu]**

The user clicks **[⬅️ Back to Task Menu]**. The bot edits the previous message to show the main task creation menu again, now with the source listed.

---

### **Step 4: Managing AI Rules**

The user is back at the main task menu and clicks **[Manage AI Rules]**.

> **Bot:**
> **Manage AI Rules for "Crypto News Feed"**
>
> Rules are applied in order. Currently, there are no AI rules.
>
> **[➕ Add AI Rule]**
> **[⬅️ Back to Task Menu]**

The user clicks **[➕ Add AI Rule]**.

> **Bot:**
> Please select the type of AI rule you want to add:
>
> **[Reword Content]** **[Summarize]**
> **[Translate]** **[Replace Watermark]**
> **[Add Header/Footer]** **[Cancel]**

The user clicks **[Summarize]**.

> **Bot:**
> **Configure: Summarize**
>
> How would you like the summary formatted?
>
> **[Paragraph]** **[Bullet Points]**
> **[⬅️ Back]**

The user clicks **[Bullet Points]**.

> **Bot:**
> **Configure: Summarize**
>
> What length should the bullet-point summary be?
>
> **[Short (1-2 points)]** **[Medium (3-5 points)]**
> **[⬅️ Back]**

The user clicks **[Medium (3-5 points)]**.

> **Bot:**
> ✅ AI Rule "Summarize" added.
>
> **Manage AI Rules for "Crypto News Feed"**
> 1. `Summarize (format: bullet_points, length: medium)` **[🗑️ Remove]**
>
> **[➕ Add Another Rule]**
> **[⬅️ Back to Task Menu]**

---

### **Step 5: Saving the Task**

The user has now configured sources, targets (in a similar flow to sources), and AI rules. They are back at the main task menu and click **[✅ Save & Enable]**.

> **Bot:**
> Please wait, I'm verifying the permissions for all sources and targets...

*(If validation is successful...)*

> **Bot:**
> ✅ All checks passed!
>
> Task "Crypto News Feed" has been created and enabled successfully. It is now live.
>
> *(The bot then shows the main menu)*

*(If validation fails...)*

> **Bot:**
> ⚠️ **Task "Crypto News Feed" could not be enabled.**
>
> I checked the channels and groups for this task and found an issue:
>
> **Source Chat: `-1001234567890`**
> - **Error:** I can't seem to access this private channel. Please make sure I have been added as an administrator with the "Read Messages" permission.
>
> Your configuration is still active in this chat. Please fix the issue and then try saving again.
>
> ---
> **Task: Crypto News Feed**
> - **Sources:** `-1001234567890`
> - **Targets:** `-1009876543210`
> - **AI Rules:** `Summarize`
> ---
> **[Manage Sources]** **[Manage Targets]**
> **[✅ Save & Enable]** **[💾 Save as Disabled]**
> **[❌ Cancel Creation]**

This detailed, stateful, and informative flow ensures that users can confidently configure complex tasks without confusion.
---
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
