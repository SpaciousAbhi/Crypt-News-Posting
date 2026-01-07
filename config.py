# config.py

import yaml


def load_tasks_from_yaml(filepath="config.yaml"):
    """
    Loads forwarding tasks from a YAML file.
    """
    try:
        with open(filepath, "r") as file:
            config = yaml.safe_load(file)
            return config.get("tasks", [])
    except FileNotFoundError:
        print(f"[Error] Configuration file not found at: {filepath}")
        return []
    except yaml.YAMLError as e:
        print(f"[Error] Failed to parse YAML configuration: {e}")
        return []


# Load tasks for the application to use
TASKS = load_tasks_from_yaml()
