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
