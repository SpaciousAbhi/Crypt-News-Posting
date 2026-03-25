# reboot_test_part2.py
from database.manager import db

def verify_persistent_task():
    tasks = db.get_tasks(999)
    found = any(t['name'] == "RebootPersistenceTest" for t in tasks)
    if found:
        print("VERIFICATION:SUCCESS")
        # Cleanup
        for t in tasks:
            if t['name'] == "RebootPersistenceTest":
                db.delete_task(t['id'])
    else:
        print("VERIFICATION:FAILED")

if __name__ == "__main__":
    verify_persistent_task()
