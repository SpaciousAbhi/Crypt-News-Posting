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
