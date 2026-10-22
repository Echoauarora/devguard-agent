import requests
from datetime import datetime

BASE_URL = "http://localhost:8080/api"


def ms_to_iso(ms_timestamp):
    """把毫秒时间戳转成后端兼容的 ISO 时间字符串，和返回格式一致"""
    return datetime.fromtimestamp(ms_timestamp / 1000).strftime("%Y-%m-%dT%H:%M:%S")


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
    def update_task_status(self, task_id, status, duration_ms=None,result_summary=None):
        """
        更新主任务状态，支持传入总耗时
        开始/结束时间由后端自动生成，保证时钟统一
        """
        url = f"{self.base_url}/task/{task_id}/status"
        params = {"status": status}
        if duration_ms is not None:
            params["durationMs"] = duration_ms
        if result_summary is not None:
            params["resultSummary"] = result_summary

        print(f"[API调试] 请求URL: {url}")
        print(f"[API调试] 传递参数: {params}")




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

#    def update_sub_task(self, sub_task_id, status, output_content=None, error_msg=None,
#                      started_at=None, finished_at=None, duration_ms=None):
#        url = f"{self.base_url}/task/subtask/{sub_task_id}"
#        body = {
#           "status": status,
#            "outputContent": output_content,
#            "errorMsg": error_msg,
#            "startedAt": started_at,
#            "finishedAt": finished_at,
#            "durationMs": duration_ms
#        }
        # 过滤空值，只更新有值的字段，避免覆盖数据库已有数据
#        body = {k: v for k, v in body.items() if v is not None}
#        resp = requests.put(url, json=body)
#        result = resp.json()
#        return result.get("code") == 200
    def update_sub_task(self, sub_id, status, output_content=None, error_msg=None,
                       started_at=None, finished_at=None, duration_ms=None, retry_count=None):
        """
        更新子任务信息，支持重试次数、错误信息
        """
        url = f"{self.base_url}/task/subtask/{sub_id}"
        body = {"status": status}
        
        if output_content is not None:
            body["outputContent"] = output_content
        if error_msg is not None:
            body["errorMsg"] = error_msg
        if started_at is not None:
            body["startedAt"] = started_at
        if finished_at is not None:
            body["finishedAt"] = finished_at
        if duration_ms is not None:
            body["durationMs"] = duration_ms
        if retry_count is not None:
            body["retryCount"] = retry_count
        
        resp = requests.put(url, json=body)
        result = resp.json()
        return result.get("code") == 200
