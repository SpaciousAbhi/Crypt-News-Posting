import yaml
from database import db

TASKS = []

def load_tasks(filepath="config.yaml"):
    """
    Loads tasks from Database primarily, falling back to YAML for initial seeding.
    """
    global TASKS
    # 1. Try loading from Database
    db_tasks = db.load_tasks()
    if db_tasks is not None:
        TASKS = db_tasks
        print(f"[Config] Loaded {len(TASKS)} tasks from Database.")
        return

    # 2. If DB is empty, try loading from YAML (Seeding)
    try:
        with open(filepath, 'r') as file:
            config = yaml.safe_load(file)
            TASKS = config.get('tasks', [])
            if TASKS:
                print(f"[Config] Seeding {len(TASKS)} tasks from {filepath} to Database.")
                db.save_tasks(TASKS)
    except FileNotFoundError:
        TASKS = []
    except yaml.YAMLError:
        TASKS = []

def save_tasks_to_yaml(filepath="config.yaml"):
    """
    Saves tasks to both Database and YAML.
    """
    # 1. Save to Database (Critical for Heroku)
    db.save_tasks(TASKS)
    
    # 2. Save to YAML (Local backup)
    try:
        with open(filepath, 'w') as file:
            yaml.dump({'tasks': TASKS}, file, sort_keys=False)
    except Exception as e:
        print(f"[Error] Failed to save YAML: {e}")

# Initial load
load_tasks()
