# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import json
# import time
# from persistence.db import DBPool
# from persistence.task_state_machine import TaskStatus, TaskStateMachine, StateTransitionError


# class TaskStore:
#     """
#     任务持久化存储
#     管理任务主表、步骤表的增删改查
#     """

#     # ========== 任务主表操作 ==========

#     @staticmethod
#     def create_task(task_type: str, input_text: str, max_steps: int = 5) -> int:
#         """
#         创建新任务，返回任务 ID
#         插入和查询自增ID在同一连接内完成，保证会话一致
#         """
#         conn = None
#         try:
#             conn = DBPool.get_conn()
#             with conn.cursor() as cursor:
#                 sql = """
#                 INSERT INTO agent_task (task_type, input, status, max_steps)
#                 VALUES (%s, %s, %s, %s)
#                 """
#                 cursor.execute(sql, (task_type, input_text, TaskStatus.PENDING.value, max_steps))
#                 conn.commit()
#                 # 同一连接内查询自增ID
#                 cursor.execute("SELECT LAST_INSERT_ID() as id")
#                 result = cursor.fetchone()
#                 return result["id"]
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#             raise e
#         finally:
#             if conn:
#                 conn.close()

#     @staticmethod
#     def get_task(task_id: int) -> dict:
#         """根据 ID 获取任务详情"""
#         sql = "SELECT * FROM agent_task WHERE id = %s"
#         result = DBPool.execute(sql, (task_id,), fetch=True)
#         return result[0] if result else None

#     @staticmethod
#     def update_status(task_id: int, target_status: str, **kwargs):
#         """
#         更新任务状态（带状态机校验）
#         可附带更新 output、error_msg、duration_ms 等字段
#         """
#         # 先查当前状态
#         task = TaskStore.get_task(task_id)
#         if not task:
#             raise ValueError(f"任务不存在：{task_id}")

#         # 状态机校验
#         TaskStateMachine.validate_transition(task["status"], target_status)

#         # 构造更新字段
#         update_fields = ["status = %s"]
#         args = [target_status]

#         if "output" in kwargs:
#             update_fields.append("output = %s")
#             args.append(kwargs["output"])
#         if "error_msg" in kwargs:
#             update_fields.append("error_msg = %s")
#             args.append(kwargs["error_msg"])
#         if "total_steps" in kwargs:
#             update_fields.append("total_steps = %s")
#             args.append(kwargs["total_steps"])
#         if "duration_ms" in kwargs:
#             update_fields.append("duration_ms = %s")
#             args.append(kwargs["duration_ms"])

#         # 终态补充完成时间
#         if target_status in [TaskStatus.SUCCESS.value, TaskStatus.FAILED.value]:
#             update_fields.append("finished_at = NOW()")

#         update_fields.append("updated_at = NOW()")
#         args.append(task_id)

#         sql = f"UPDATE agent_task SET {', '.join(update_fields)} WHERE id = %s"
#         DBPool.execute(sql, tuple(args))

#     @staticmethod
#     def list_running_tasks() -> list:
#         """获取所有执行中的任务（用于进程启动时恢复）"""
#         sql = "SELECT * FROM agent_task WHERE status = %s ORDER BY created_at ASC"
#         return DBPool.execute(sql, (TaskStatus.RUNNING.value,), fetch=True)

#     # ========== 任务步骤表操作 ==========

#     @staticmethod
#     def add_step(task_id: int, step_num: int, step_type: str, tool_name: str = None, input_snapshot: str = None):
#         """新增一个步骤，状态为 PENDING"""
#         sql = """
#         INSERT INTO agent_task_step (task_id, step_num, step_type, tool_name, input_snapshot, status)
#         VALUES (%s, %s, %s, %s, %s, %s)
#         """
#         DBPool.execute(sql, (
#             task_id, step_num, step_type, tool_name, input_snapshot, TaskStatus.PENDING.value
#         ))

#     @staticmethod
#     def update_step_success(task_id: int, step_num: int, output_snapshot: str, duration_ms: int):
#         """标记步骤执行成功，保存输出快照"""
#         sql = """
#         UPDATE agent_task_step 
#         SET status = %s, output_snapshot = %s, duration_ms = %s, finished_at = NOW()
#         WHERE task_id = %s AND step_num = %s
#         """
#         DBPool.execute(sql, (
#             TaskStatus.SUCCESS.value, output_snapshot, duration_ms, task_id, step_num
#         ))

#     @staticmethod
#     def update_step_failed(task_id: int, step_num: int, error_msg: str, duration_ms: int):
#         """标记步骤执行失败，保存错误信息"""
#         sql = """
#         UPDATE agent_task_step 
#         SET status = %s, error_msg = %s, duration_ms = %s, finished_at = NOW()
#         WHERE task_id = %s AND step_num = %s
#         """
#         DBPool.execute(sql, (
#             TaskStatus.FAILED.value, error_msg, duration_ms, task_id, step_num
#         ))

#     @staticmethod
#     def list_success_steps(task_id: int) -> list:
#         """获取任务所有成功的步骤，按步骤号排序（用于恢复上下文）"""
#         sql = """
#         SELECT * FROM agent_task_step 
#         WHERE task_id = %s AND status = %s 
#         ORDER BY step_num ASC
#         """
#         return DBPool.execute(sql, (task_id, TaskStatus.SUCCESS.value), fetch=True)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from persistence.db import DBPool
from persistence.task_state_machine import TaskStatus, TaskStateMachine, StateTransitionError


class TaskStore:
    """
    任务持久化存储
    管理任务主表、步骤表的增删改查
    """

    # ========== 任务主表操作 ==========

    @staticmethod
    def create_task(task_type: str, input_text: str, max_steps: int = 5) -> int:
        """
        创建新任务，返回任务 ID
        插入和查询自增ID在同一连接内完成，保证会话一致
        """
        conn = None
        try:
            conn = DBPool.get_conn()
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO agent_task (task_type, input, status, max_steps)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (task_type, input_text, TaskStatus.PENDING.value, max_steps))
                conn.commit()
                # 同一连接内查询自增ID
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                result = cursor.fetchone()
                return result["id"]
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_task(task_id: int) -> dict:
        """根据 ID 获取任务详情"""
        sql = "SELECT * FROM agent_task WHERE id = %s"
        result = DBPool.execute(sql, (task_id,), fetch=True)
        return result[0] if result else None

    @staticmethod
    def update_status(task_id: int, target_status: str, **kwargs):
        """
        更新任务状态（带状态机校验）
        可附带更新 output、error_msg、duration_ms 等字段
        """
        # 先查当前状态
        task = TaskStore.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在：{task_id}")

        # ========== 核心兜底：同状态直接跳过，不触发校验 ==========
        if task["status"] == target_status:
            return

        # 状态机校验
        TaskStateMachine.validate_transition(task["status"], target_status)

        # 构造更新字段
        update_fields = ["status = %s"]
        args = [target_status]

        if "output" in kwargs:
            update_fields.append("output = %s")
            args.append(kwargs["output"])
        if "error_msg" in kwargs:
            update_fields.append("error_msg = %s")
            args.append(kwargs["error_msg"])
        if "total_steps" in kwargs:
            update_fields.append("total_steps = %s")
            args.append(kwargs["total_steps"])
        if "duration_ms" in kwargs:
            update_fields.append("duration_ms = %s")
            args.append(kwargs["duration_ms"])

        # 终态补充完成时间
        if target_status in [TaskStatus.SUCCESS.value, TaskStatus.FAILED.value]:
            update_fields.append("finished_at = NOW()")

        update_fields.append("updated_at = NOW()")
        args.append(task_id)

        sql = f"UPDATE agent_task SET {', '.join(update_fields)} WHERE id = %s"
        DBPool.execute(sql, tuple(args))

    @staticmethod
    def list_running_tasks() -> list:
        """获取所有执行中的任务（用于进程启动时恢复）"""
        sql = "SELECT * FROM agent_task WHERE status = %s ORDER BY created_at ASC"
        return DBPool.execute(sql, (TaskStatus.RUNNING.value,), fetch=True)

    # ========== 任务步骤表操作 ==========

    @staticmethod
    def add_step(task_id: int, step_num: int, step_type: str, tool_name: str = None, input_snapshot: str = None):
        """新增一个步骤，状态为 PENDING"""
        sql = """
        INSERT INTO agent_task_step (task_id, step_num, step_type, tool_name, input_snapshot, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        DBPool.execute(sql, (
            task_id, step_num, step_type, tool_name, input_snapshot, TaskStatus.PENDING.value
        ))

    @staticmethod
    def update_step_success(task_id: int, step_num: int, output_snapshot: str, duration_ms: int):
        """标记步骤执行成功，保存输出快照"""
        sql = """
        UPDATE agent_task_step 
        SET status = %s, output_snapshot = %s, duration_ms = %s, finished_at = NOW()
        WHERE task_id = %s AND step_num = %s
        """
        DBPool.execute(sql, (
            TaskStatus.SUCCESS.value, output_snapshot, duration_ms, task_id, step_num
        ))

    @staticmethod
    def update_step_failed(task_id: int, step_num: int, error_msg: str, duration_ms: int):
        """标记步骤执行失败，保存错误信息"""
        sql = """
        UPDATE agent_task_step 
        SET status = %s, error_msg = %s, duration_ms = %s, finished_at = NOW()
        WHERE task_id = %s AND step_num = %s
        """
        DBPool.execute(sql, (
            TaskStatus.FAILED.value, error_msg, duration_ms, task_id, step_num
        ))

    @staticmethod
    def list_success_steps(task_id: int) -> list:
        """获取任务所有成功的步骤，按步骤号排序（用于恢复上下文）"""
        sql = """
        SELECT * FROM agent_task_step 
        WHERE task_id = %s AND status = %s 
        ORDER BY step_num ASC
        """
        return DBPool.execute(sql, (task_id, TaskStatus.SUCCESS.value), fetch=True)
