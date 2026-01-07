# config.py

import yaml

TASKS = []

def load_tasks_from_yaml(filepath="config.yaml"):
    """
    Loads forwarding tasks from a YAML file.
    """
    global TASKS
    try:
        with open(filepath, 'r') as file:
            config = yaml.safe_load(file)
            TASKS = config.get('tasks', [])
    except FileNotFoundError:
        print(f"[Error] Configuration file not found at: {filepath}")
        TASKS = []
    except yaml.YAMLError as e:
        print(f"[Error] Failed to parse YAML configuration: {e}")
        TASKS = []

def save_tasks_to_yaml(filepath="config.yaml"):
    """
    Saves the current tasks to a YAML file.
    """
    try:
        with open(filepath, 'w') as file:
            yaml.dump({'tasks': TASKS}, file, sort_keys=False)
    except Exception as e:
        print(f"[Error] Failed to save configuration: {e}")

# Initial load of tasks
load_tasks_from_yaml()
