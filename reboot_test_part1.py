# reboot_test_part1.py
from database.manager import db
import sys

def create_persistent_task():
    task_id = db.create_task("RebootPersistenceTest", 999, {"reboot": True})
    print(f"TASK_ID:{task_id}")

if __name__ == "__main__":
    create_persistent_task()
