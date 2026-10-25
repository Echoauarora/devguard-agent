import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence.db import DBPool


class TraceLogger:
    """
    全链路轨迹日志
    所有执行事件统一埋点，永久留存，用于排查、监控、统计
    """

    @staticmethod
    def log(task_id: int, event_type: str, event_detail: str = None, step_num: int = None, duration_ms: int = None, extra: str = None):
        """
        记录一条轨迹日志
        """
        sql = """
        INSERT INTO agent_trace_log (task_id, step_num, event_type, event_detail, duration_ms, extra)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        DBPool.execute(sql, (
            task_id, step_num, event_type, event_detail, duration_ms, extra
        ))

    # ========== 快捷方法 ==========

    @staticmethod
    def task_create(task_id: int, input_text: str):
        TraceLogger.log(task_id, "TASK_CREATE", f"任务创建，输入长度：{len(input_text)}")

    @staticmethod
    def task_start(task_id: int):
        TraceLogger.log(task_id, "TASK_START", "任务开始执行")

    @staticmethod
    def reasoning_start(task_id: int, step_num: int, msg_count: int):
        TraceLogger.log(task_id, "REASONING_START", f"第{step_num}步推理开始，当前消息数：{msg_count}", step_num=step_num)

    @staticmethod
    def tool_call_start(task_id: int, step_num: int, tool_name: str):
        TraceLogger.log(task_id, "TOOL_CALL_START", f"调用工具：{tool_name}", step_num=step_num)

    @staticmethod
    def tool_call_end(task_id: int, step_num: int, tool_name: str, success: bool, duration_ms: int):
        detail = f"工具 {tool_name} 执行{'成功' if success else '失败'}，耗时：{duration_ms}ms"
        TraceLogger.log(task_id, "TOOL_CALL_END", detail, step_num=step_num, duration_ms=duration_ms)

    @staticmethod
    def task_success(task_id: int, total_steps: int, duration_ms: int):
        detail = f"任务成功完成，总步数：{total_steps}，总耗时：{duration_ms}ms"
        TraceLogger.log(task_id, "TASK_SUCCESS", detail, duration_ms=duration_ms)

    @staticmethod
    def task_fail(task_id: int, error_msg: str, duration_ms: int):
        detail = f"任务失败，错误：{error_msg}"
        TraceLogger.log(task_id, "TASK_FAIL", detail, duration_ms=duration_ms)
