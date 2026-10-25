import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from llm.llm_client import LLMClient
from tools.tool_registry import ToolRegistry
from tools.tool_executor import ToolExecutor


class SimpleAgent:
    """
    单轮工具调用 Agent
    演示完整的 Function Calling 流程


    增加参数校验，超时控制，失败重试，异常兜底
    """

    def __init__(self):
        self.llm = LLMClient()
        self.tool_registry = ToolRegistry()
        self.tool_executor = ToolExecutor( 
            self.tool_registry,
            max_retry=2,
            timeout=30
        )
        self.system_prompt = """
你是 DevGuard 代码工程诊断助手。
你可以使用提供的工具来分析代码问题。
如果用户需要分析代码，请先调用代码扫描工具获取问题列表，再基于结果给出详细的诊断报告和修复建议。
注意：所有结论必须基于工具返回的结果，禁止凭空编造问题。
如果工具执行出错，请把错误信息告知用户
"""

    def run(self, user_input: str) -> str:
        # 1. 构造初始对话
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

        # 2. 调用大模型，判断是否调用工具
        tool_defs = self.tool_registry.get_tool_definitions()
        #第一次调用大模型
        try:

            response = self.llm.chat_with_function(messages, tool_defs)

        except Exception as e:

            return f"大模型调用失败：{e}"

        # 3. 如果大模型决定调用工具
        if response.get("tool_calls"):
            try:
                tool_call = response["tool_calls"][0]
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
            except Exception as e:
                return f"工具调用失败指令解析失败：{str(e)}"

            print(f"[Agent] 大模型决策调用工具：{tool_name}")

            # 4. 执行工具
            tool_result = self.tool_executor.execute(tool_name, arguments)
            print(f"[Agent] 工具执行完成")

            # 5. 回填对话历史
            messages.append({
                "role": "assistant",
                "tool_calls": response["tool_calls"]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

            # 6. 二次调用大模型生成最终答案
            try:
                final_resp = self.llm.chat_with_function(messages, tool_defs)
                return final_resp.get("content", "生成失败")
            except Exception as e:
                return f"结果生成失败：{str(e)}"
        # 不需要调用工具，直接返回
        return response.get("content", "")
