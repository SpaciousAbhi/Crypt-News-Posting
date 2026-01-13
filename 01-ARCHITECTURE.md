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
