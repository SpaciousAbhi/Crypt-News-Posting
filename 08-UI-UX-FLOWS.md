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
