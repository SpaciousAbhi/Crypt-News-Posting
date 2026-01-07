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
