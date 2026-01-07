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
