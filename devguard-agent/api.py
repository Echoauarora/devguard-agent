# import requests
# from datetime import datetime

# BASE_URL = "http://localhost:8080/api"


# def ms_to_iso(ms_timestamp):
#     """把毫秒时间戳转成后端兼容的 ISO 时间字符串，和返回格式一致"""
#     return datetime.fromtimestamp(ms_timestamp / 1000).strftime("%Y-%m-%dT%H:%M:%S")


# class TaskApi:
#     def __init__(self):
#         self.base_url = BASE_URL

#     def get_pending_tasks(self):
#         url = f"{self.base_url}/task/pending"
#         resp = requests.get(url)
#         result = resp.json()
#         if result.get("code") == 200:
#             return result.get("data", [])
#         return []
#     def update_task_status(self, task_id, status, duration_ms=None,result_summary=None):
#         """
#         更新主任务状态，支持传入总耗时
#         开始/结束时间由后端自动生成，保证时钟统一
#         """
#         url = f"{self.base_url}/task/{task_id}/status"
#         params = {"status": status}
#         if duration_ms is not None:
#             params["durationMs"] = duration_ms
#         if result_summary is not None:
#             params["resultSummary"] = result_summary

#         print(f"[API调试] 请求URL: {url}")
#         print(f"[API调试] 传递参数: {params}")




#         resp = requests.put(url, params=params)
#         result = resp.json()
#         return result.get("code") == 200


#     def get_sub_tasks(self, task_id):
#         url = f"{self.base_url}/task/{task_id}/subtasks"
#         resp = requests.get(url)
#         result = resp.json()
#         if result.get("code") == 200:
#             return result.get("data", [])
#         return []

# #    def update_sub_task(self, sub_task_id, status, output_content=None, error_msg=None,
# #                      started_at=None, finished_at=None, duration_ms=None):
# #        url = f"{self.base_url}/task/subtask/{sub_task_id}"
# #        body = {
# #           "status": status,
# #            "outputContent": output_content,
# #            "errorMsg": error_msg,
# #            "startedAt": started_at,
# #            "finishedAt": finished_at,
# #            "durationMs": duration_ms
# #        }
#         # 过滤空值，只更新有值的字段，避免覆盖数据库已有数据
# #        body = {k: v for k, v in body.items() if v is not None}
# #        resp = requests.put(url, json=body)
# #        result = resp.json()
# #        return result.get("code") == 200
#     def update_sub_task(self, sub_id, status, output_content=None, error_msg=None,
#                        started_at=None, finished_at=None, duration_ms=None, retry_count=None):
#         """
#         更新子任务信息，支持重试次数、错误信息
#         """
#         url = f"{self.base_url}/task/subtask/{sub_id}"
#         body = {"status": status}
        
#         if output_content is not None:
#             body["outputContent"] = output_content
#         if error_msg is not None:
#             body["errorMsg"] = error_msg
#         if started_at is not None:
#             body["startedAt"] = started_at
#         if finished_at is not None:
#             body["finishedAt"] = finished_at
#         if duration_ms is not None:
#             body["durationMs"] = duration_ms
#         if retry_count is not None:
#             body["retryCount"] = retry_count
        
#         resp = requests.put(url, json=body)
#         result = resp.json()
#         return result.get("code") == 200
import os
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "7299018")  # 改成你本地的真实密码
os.environ.setdefault("DB_NAME", "devguard")

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from agent.persistent_planner_agent import PersistentPlannerAgent
from persistence.task_store import TaskStore
from persistence.task_state_machine import TaskStatus


app = FastAPI(title="DevGuard 代码诊断 Agent API")


# ===================== 工具函数：数据库字段转驼峰 =====================
def task_to_camel(task: dict) -> dict:
    return {
        "taskId": task["id"],
        "taskType": task["task_type"],
        "status": task["status"],
        "totalSteps": task["total_steps"],
        "maxSteps": task["max_steps"],
        "durationMs": task["duration_ms"],
        "errorMsg": task["error_msg"],
        "resultSummary": task["output"][:100] if task["output"] else None,
        "createdAt": task["created_at"].isoformat() if task["created_at"] else None,
        "finishedAt": task["finished_at"].isoformat() if task["finished_at"] else None,
    }


def step_to_camel(step: dict) -> dict:
    return {
        "subId": step["id"],
        "taskId": step["task_id"],
        "stepNum": step["step_num"],
        "stepType": step["step_type"],
        "toolName": step["tool_name"],
        "status": step["status"],
        "outputContent": step["output_snapshot"],
        "errorMsg": step["error_msg"],
        "durationMs": step["duration_ms"],
        "createdAt": step["created_at"].isoformat() if step["created_at"] else None,
        "finishedAt": step["finished_at"].isoformat() if step["finished_at"] else None,
    }


# ===================== 1. 获取待处理任务列表 =====================
@app.get("/api/task/pending")
def get_pending_tasks():
    """
    获取所有 PENDING 状态的任务，对应客户端 get_pending_tasks
    """
    sql = "SELECT * FROM agent_task WHERE status = %s ORDER BY created_at ASC"
    from persistence.db import DBPool
    tasks = DBPool.execute(sql, (TaskStatus.PENDING.value,), fetch=True)
    return {
        "code": 200,
        "data": [task_to_camel(t) for t in tasks]
    }


# ===================== 2. 更新主任务状态 =====================
@app.put("/api/task/{task_id}/status")
def update_task_status(
    task_id: int,
    status: str = Query(...),
    durationMs: Optional[int] = Query(None),
    resultSummary: Optional[str] = Query(None),
):
    """
    更新主任务状态、总耗时、结果摘要，对应客户端 update_task_status
    时间由后端自动生成，保证时钟统一
    """
    task = TaskStore.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_kwargs = {}
    if durationMs is not None:
        update_kwargs["duration_ms"] = durationMs
    if resultSummary is not None:
        update_kwargs["output"] = resultSummary

    try:
        TaskStore.update_status(task_id, status, **update_kwargs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"code": 200, "data": {"task_id": task_id, "status": status}}


# ===================== 3. 获取任务的子任务（步骤）列表 =====================
@app.get("/api/task/{task_id}/subtasks")
def get_sub_tasks(task_id: int):
    """
    获取指定任务的所有执行步骤（子任务），对应客户端 get_sub_tasks
    """
    task = TaskStore.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    steps = TaskStore.list_success_steps(task_id)
    return {
        "code": 200,
        "data": [step_to_camel(s) for s in steps]
    }


# ===================== 4. 更新子任务（步骤）详情 =====================
class SubTaskUpdate(BaseModel):
    status: str
    outputContent: Optional[str] = None
    errorMsg: Optional[str] = None
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    durationMs: Optional[int] = None
    retryCount: Optional[int] = None


@app.put("/api/task/subtask/{sub_id}")
def update_sub_task(sub_id: int, body: SubTaskUpdate):
    """
    更新子任务的状态、输出、错误、耗时、重试次数，对应客户端 update_sub_task
    """
    from persistence.db import DBPool

    # 构造更新字段
    update_fields = []
    args = []

    if body.status is not None:
        update_fields.append("status = %s")
        args.append(body.status)
    if body.outputContent is not None:
        update_fields.append("output_snapshot = %s")
        args.append(body.outputContent)
    if body.errorMsg is not None:
        update_fields.append("error_msg = %s")
        args.append(body.errorMsg)
    if body.durationMs is not None:
        update_fields.append("duration_ms = %s")
        args.append(body.durationMs)

    if not update_fields:
        return {"code": 200, "data": {"sub_id": sub_id}}

    args.append(sub_id)
    sql = f"UPDATE agent_task_step SET {', '.join(update_fields)} WHERE id = %s"

    try:
        DBPool.execute(sql, tuple(args))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"code": 200, "data": {"sub_id": sub_id, "status": body.status}}


# ===================== 附加：提交任务接口（兼容原有能力） =====================
class DiagnoseRequest(BaseModel):
    code: str
    max_steps: int = 5


@app.post("/api/task")
def submit_task(req: DiagnoseRequest):
    """
    提交代码诊断任务，创建后异步执行
    """
    user_input = f"帮我全面诊断这段Java代码，先统计代码结构信息，再扫描所有问题，最后给出完整的修复报告：\n{req.code}"
    task_id = TaskStore.create_task("code_diagnose", user_input, req.max_steps)

    # 后台异步执行
    import threading
    agent = PersistentPlannerAgent(max_steps=req.max_steps)
    threading.Thread(target=agent.run_by_id, args=(task_id,), daemon=True).start()

    return {"code": 200, "data": {"taskId": task_id, "status": "PENDING"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
