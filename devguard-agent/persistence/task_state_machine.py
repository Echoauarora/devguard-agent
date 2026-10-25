from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class StateTransitionError(Exception):
    """非法状态流转异常"""
    pass


class TaskStateMachine:
    """
    任务状态机
    严格约束状态流转规则，所有状态变更必须通过本类
    """

    # 允许的状态流转映射：当前状态 -> 允许的下一个状态列表
    _ALLOWED_TRANSITIONS = {
        TaskStatus.PENDING: [TaskStatus.RUNNING, TaskStatus.FAILED],
        TaskStatus.RUNNING: [TaskStatus.SUCCESS, TaskStatus.FAILED],
        TaskStatus.SUCCESS: [],
        TaskStatus.FAILED: []
    }

    @classmethod
    def can_transition(cls, current_status: str, target_status: str) -> bool:
        """检查是否允许从当前状态流转到目标状态"""
        try:
            current = TaskStatus(current_status)
            target = TaskStatus(target_status)
        except ValueError:
            return False
        return target in cls._ALLOWED_TRANSITIONS[current]

    @classmethod
    def validate_transition(cls, current_status: str, target_status: str):
        """校验状态流转，不合法直接抛异常"""
        if not cls.can_transition(current_status, target_status):
            raise StateTransitionError(
                f"非法状态流转：{current_status} → {target_status}"
            )
