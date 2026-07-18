def find_tasks(data: dict, keyword: str):
    results = []

    for branch_name, tasks in data.get("branches", {}).items():
        for task in tasks:
            if keyword in task.get("name", ""):
                results.append({
                    "branch": branch_name,
                    "task": task
                })

    return results