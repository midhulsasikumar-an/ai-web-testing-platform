import uuid
from datetime import datetime
from backend.database.mongo import bug_collection


def create_bugs_from_test(test_data):
    created_bugs = []

    for result in test_data.get("results", []):

        if result["status"] == "fail":

            bug = {
                "bug_id": str(uuid.uuid4()),

                "test_id": test_data["test_id"],

                "user_id": test_data["user_id"],

                "title": result["test"],

                "description": result.get("details", "No details provided"),

                "severity": "medium",

                "status": "open",

                "url": test_data["url"],

                "created_at": datetime.utcnow().isoformat()
            }

            bug_collection.insert_one(bug)

            created_bugs.append(bug)

    return created_bugs