import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import concurrent.futures
from tools.tool_registry import ToolRegistry


class ToolExecutionError(Exception):
    """工具执行统一异常类"""
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(f"[{error_type}] {message}")


class ToolExecutor:
    """
    工程化工具执行器
    提供参数校验、超时控制、失败重试、统一异常处理
    """

    def __init__(self, registry: ToolRegistry, max_retry: int = 2, timeout: int = 30):
        self.registry = registry
        self.max_retry = max_retry
        self.timeout = timeout
        self._tool_defs = {
            t["function"]["name"]: t["function"]
            for t in registry.get_tool_definitions()
        }

    def execute(self, tool_name: str, arguments: dict) -> str:
        """
        工程化执行工具
        返回：工具执行结果字符串；失败则返回标准化错误信息
        """
        # 1. 校验工具是否存在
        if tool_name not in self._tool_defs:
            return str(ToolExecutionError("UNKNOWN_TOOL", f"未知工具：{tool_name}"))

        # 2. 参数校验
        try:
            self._validate_params(tool_name, arguments)
        except ToolExecutionError as e:
            return str(e)

        # 3. 带重试 + 超时执行
        last_error = None
        for retry in range(self.max_retry + 1):
            try:
                result = self._run_with_timeout(tool_name, arguments)
                return result
            except ToolExecutionError as e:
                last_error = e
                if e.error_type not in ["PARAM_ERROR", "UNKNOWN_TOOL"]:
                    continue
                break
            except Exception as e:
                last_error = ToolExecutionError("EXEC_ERROR", str(e))
                continue

        return str(last_error)

    def _validate_params(self, tool_name: str, arguments: dict):
        """校验参数是否符合工具定义"""
        tool_def = self._tool_defs[tool_name]
        params_def = tool_def["parameters"]
        required = params_def.get("required", [])

        for param in required:
            if param not in arguments:
                raise ToolExecutionError(
                    "PARAM_ERROR",
                    f"缺少必填参数：{param}"
                )

    def _run_with_timeout(self, tool_name: str, arguments: dict) -> str:
        """带超时控制执行工具"""
        def _target():
            return self.registry.execute_tool(tool_name, arguments)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_target)
            try:
                return future.result(timeout=self.timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise ToolExecutionError(
                    "TIMEOUT",
                    f"工具执行超时，限制{self.timeout}秒"
                )
