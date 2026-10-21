import requests

BASE_URL = "http://localhost:8080/api"


class TaskApi:
    def __init__(self):
        self.base_url = BASE_URL

    def get_pending_tasks(self):
        url = f"{self.base_url}/task/pending"
        resp = requests.get(url)
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data", [])
        return []

    def update_task_status(self, task_id, status):
        url = f"{self.base_url}/task/{task_id}/status"
        params = {"status": status}
        resp = requests.put(url, params=params)
        result = resp.json()
        return result.get("code") == 200

    def get_sub_tasks(self, task_id):
        url = f"{self.base_url}/task/{task_id}/subtasks"
        resp = requests.get(url)
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data", [])
        return []

    def update_sub_task(self, sub_task_id, status, output_content=None, error_msg=None):
        url = f"{self.base_url}/task/subtask/{sub_task_id}"
        body = {
            "status": status,
            "outputContent": output_content,
            "errorMsg": error_msg
        }
        resp = requests.put(url, json=body)
        result = resp.json()
        return result.get("code") == 200
