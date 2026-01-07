# Advanced AI Forwarding Bot for Telegram

This bot monitors messages from a set of source Telegram channels, modifies them using AI, and forwards them to one or more target Telegram channels. It's designed to be highly configurable and supports multiple, concurrent forwarding tasks.

## Features

-   **Multi-Task Support**: Run multiple forwarding tasks at once, each with its own sources, targets, and AI rules.
-   **Flexible Configuration**: Define all tasks in a simple `config.yaml` file, or add new tasks on the fly with the inline button interface.
-   **AI-Powered Modifications**:
    -   **Reword**: Rephrase content for clarity and engagement.
    -   **Summarize**: Condense long messages into concise summaries.
    -   **Add Headers/Footers**: Automatically prepend or append text.
    -   **Replace Watermarks**: Swap out text like "Source.com" with "MyBrand".
-   **Interactive Bot Commands**: Manage and monitor the bot directly from Telegram.
-   **Code Quality**: Includes linting, formatting, and unit tests to ensure reliability.

## Setup

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a Virtual Environment** (Recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Copy the example `.env.example` file to `.env` and fill in your API keys.
    ```bash
    cp .env.example .env
    ```
    -   `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather.
    -   `GROQ_API_KEY`: Your API key for the Groq AI service.

5.  **Configure Tasks**
    Open `config.yaml` and define your forwarding tasks. The file contains examples to get you started. Each task should include:
    -   `name`: A descriptive name for the task.
    -   `sources`: A list of source channel IDs.
    -   `targets`: A list of target channel IDs.
    -   `ai_options`: A dictionary of AI modifications to apply.

    **How to Find a Telegram Channel ID:**
    1.  Forward a message from the channel to a bot like `@userinfobot`.
    2.  The bot will reply with the channel's ID (it's usually a negative number).
    3.  Add the bot to the source channels as an administrator so that it can receive messages.

## Running the Bot

Once you have completed the setup, you can run the bot with:
```bash
python main.py
```
The bot will start listening for new messages in the source channels.

## Interactive Commands

You can interact with the bot directly in Telegram by sending the `/start` command. This will open a menu of inline buttons that will allow you to:

-   **View Tasks**: Displays a list of all current forwarding tasks.
-   **Add a New Task**: Initiates a conversation to create a new task.
-   **Remove a Task**: Allows you to select and delete an existing task.
-   **Help**: Shows detailed instructions.

## Development

This project includes tools for maintaining code quality.

1.  **Install Development Dependencies**
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Running Tests**
    To ensure everything is working correctly, you can run the unit tests:
    ```bash
    python -m unittest discover tests
    ```

3.  **Code Formatting and Linting**
    -   To format the code, use `black`:
        ```bash
        black .
        ```
    -   To check for style issues, use `flake8`:
        ```bash
        flake8 .
        ```
