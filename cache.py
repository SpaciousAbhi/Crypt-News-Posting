# cache.py

from database import SessionLocal, Task

TASKS = []

def load_tasks():
    """Loads tasks from the database into the in-memory cache."""
    global TASKS
    db = SessionLocal()
    TASKS = db.query(Task).all()
    db.close()
