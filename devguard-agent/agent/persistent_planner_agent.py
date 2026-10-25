# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import json
# import time
# from llm.llm_client import LLMClient
# from tools.tool_registry import ToolRegistry
# from tools.tool_executor import ToolExecutor
# from persistence.task_store import TaskStore
# from persistence.task_state_machine import TaskStatus
# from persistence.trace_logger import TraceLogger


# class PersistentPlannerAgent:
#     """
#     持久化多步骤规划 Agent
#     基于 ReAct 模式，集成状态机、全链路埋点、步骤快照、断点恢复
#     """

#     def __init__(self, max_steps: int = 5):
#         self.llm = LLMClient()
#         self.tool_registry = ToolRegistry()
#         self.tool_executor = ToolExecutor(
#             self.tool_registry,
#             max_retry=2,
#             timeout=30
#         )
#         self.max_steps = max_steps
#         self.system_prompt = """
# 你是 DevGuard 代码工程诊断助手。
# 你可以使用提供的工具来分析代码问题。

# 严格执行以下规则：
# 1.  任务固定三步走：
#     第一步：调用 java_code_structure 统计代码结构信息
#     第二步：调用 java_code_scan 扫描代码问题
#     第三步：基于前两步的工具结果，输出完整的诊断报告和修复建议
# 2.  每个工具只调用一次，已经获取的结果直接使用，禁止重复调用相同工具
# 3.  所有结论必须基于工具返回的结果，禁止凭空编造问题
# 4.  工具返回结果开头会标记【工具执行成功】或【工具执行失败】，请根据标记判断执行状态
# 5.  如果工具执行失败，请把错误信息告知用户，不要编造结果

# 按步骤执行，不要跳过，不要重复。
# """

#     def run_by_id(self, task_id: int) -> str:
#         """
#         根据任务 ID 执行任务（支持断点恢复）
#         """
#         task = TaskStore.get_task(task_id)
#         if not task:
#             return f"任务不存在：{task_id}"

#         # 状态校验：只有 PENDING / RUNNING 可以执行
#         if task["status"] not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
#             return f"任务状态为 {task['status']}，无法执行"

#         start_time = time.time()

#         # 标记任务开始执行
#         TaskStore.update_status(task_id, TaskStatus.RUNNING.value)
#         TraceLogger.task_start(task_id)

#         # 重建对话历史：有成功步骤就从断点恢复，没有就从头开始
#         messages = self._rebuild_messages(task)
#         tool_defs = self.tool_registry.get_tool_definitions()

#         # 计算从第几步开始
#         success_steps = TaskStore.list_success_steps(task_id)
#         start_step = len(success_steps)

#         total_steps = 0
#         try:
#             # ReAct 循环
#             for step in range(start_step, self.max_steps):
#                 step_num = step + 1
#                 total_steps = step_num

#                 print(f"\n[Agent] 第 {step_num} 步推理中...")
#                 TraceLogger.reasoning_start(task_id, step_num, len(messages))

#                 # 1. 调用大模型思考
#                 try:
#                     response = self.llm.chat_with_function(messages, tool_defs)
#                 except Exception as e:
#                     raise Exception(f"大模型调用失败：{str(e)}")

#                 # 2. 不需要调用工具 = 任务完成
#                 if not response.get("tool_calls"):
#                     print("[Agent] 任务完成，生成最终报告")
#                     result = response.get("content", "生成失败")

#                     # 更新任务状态为成功
#                     duration_ms = int((time.time() - start_time) * 1000)
#                     TaskStore.update_status(
#                         task_id, TaskStatus.SUCCESS.value,
#                         output=result,
#                         total_steps=total_steps,
#                         duration_ms=duration_ms
#                     )
#                     TraceLogger.task_success(task_id, total_steps, duration_ms)
#                     return result

#                 # 3. 先把 assistant 消息加入历史
#                 messages.append({
#                     "role": "assistant",
#                     "content": response["content"],
#                     "tool_calls": response["tool_calls"]
#                 })

#                 # 4. 遍历执行所有工具调用
#                 for tool_call in response["tool_calls"]:
#                     tool_name = tool_call["function"]["name"]
#                     try:
#                         arguments = json.loads(tool_call["function"]["arguments"])
#                     except Exception as e:
#                         raise Exception(f"工具指令解析失败：{str(e)}")

#                     print(f"[Agent] 调用工具：{tool_name}")
#                     TraceLogger.tool_call_start(task_id, step_num, tool_name)

#                     tool_start = time.time()

#                     # 工程化执行工具
#                     tool_result = self.tool_executor.execute(tool_name, arguments)
#                     success = "【工具执行成功】" in tool_result

#                     tool_duration = int((time.time() - tool_start) * 1000)
#                     TraceLogger.tool_call_end(task_id, step_num, tool_name, success, tool_duration)

#                     print(f"[Agent] 工具 {tool_name} 执行完成")

#                     # 每个工具对应一条 tool 消息
#                     messages.append({
#                         "role": "tool",
#                         "tool_call_id": tool_call["id"],
#                         "content": str(tool_result)
#                     })

#                 # 5. 本步执行完成，保存步骤快照
#                 TaskStore.add_step(
#                     task_id, step_num, "tool_call",
#                     tool_name=tool_name,
#                     input_snapshot=json.dumps(response["tool_calls"], ensure_ascii=False)
#                 )
#                 TaskStore.update_step_success(
#                     task_id, step_num,
#                     output_snapshot=str(tool_result),
#                     duration_ms=int((time.time() - start_time) * 1000)
#                 )

#             # 超过最大步数
#             duration_ms = int((time.time() - start_time) * 1000)
#             error_msg = f"任务执行超过最大步数限制（{self.max_steps}步）"
#             TaskStore.update_status(
#                 task_id, TaskStatus.FAILED.value,
#                 error_msg=error_msg,
#                 total_steps=total_steps,
#                 duration_ms=duration_ms
#             )
#             TraceLogger.task_fail(task_id, error_msg, duration_ms)
#             return error_msg

#         except Exception as e:
#             # 全局异常捕获，标记任务失败
#             duration_ms = int((time.time() - start_time) * 1000)
#             error_msg = str(e)
#             TaskStore.update_status(
#                 task_id, TaskStatus.FAILED.value,
#                 error_msg=error_msg,
#                 total_steps=total_steps,
#                 duration_ms=duration_ms
#             )
#             TraceLogger.task_fail(task_id, error_msg, duration_ms)
#             return f"任务执行失败：{error_msg}"

#     def run_new_task(self, input_text: str, task_type: str = "code_diagnose") -> str:
#         """
#         创建新任务并执行
#         """
#         task_id = TaskStore.create_task(task_type, input_text, self.max_steps)
#         TraceLogger.task_create(task_id, input_text)
#         print(f"[Agent] 任务已创建，ID：{task_id}")
#         return self.run_by_id(task_id)

#     def _rebuild_messages(self, task: dict) -> list:
#         """
#         根据历史步骤重建对话上下文（断点恢复核心）
#         """
#         messages = [
#             {"role": "system", "content": self.system_prompt},
#             {"role": "user", "content": task["input"]}
#         ]

#         # 加载所有成功的步骤，还原对话历史
#         steps = TaskStore.list_success_steps(task["id"])
#         for step in steps:
#             # 还原 assistant 工具调用消息
#             if step["input_snapshot"]:
#                 try:
#                     tool_calls = json.loads(step["input_snapshot"])
#                     messages.append({
#                         "role": "assistant",
#                         "content": "",
#                         "tool_calls": tool_calls
#                     })
#                 except:
#                     pass

#             # 还原 tool 结果消息
#             if step["output_snapshot"] and step["tool_name"]:
#                 messages.append({
#                     "role": "tool",
#                     "tool_call_id": f"step_{step['step_num']}",
#                     "content": step["output_snapshot"]
#                 })

#         return messages

#     @staticmethod
#     def recover_running_tasks():
#         """
#         进程启动时恢复所有中断的任务
#         扫描 RUNNING 状态的任务，逐个继续执行
#         """
#         running_tasks = TaskStore.list_running_tasks()
#         if not running_tasks:
#             print("[恢复] 没有需要恢复的任务")
#             return

#         print(f"[恢复] 发现 {len(running_tasks)} 个中断任务，开始恢复...")
#         agent = PersistentPlannerAgent()
#         for task in running_tasks:
#             print(f"[恢复] 继续执行任务 {task['id']}")
#             agent.run_by_id(task["id"])
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from llm.llm_client import LLMClient
from tools.tool_registry import ToolRegistry
from tools.tool_executor import ToolExecutor
from persistence.task_store import TaskStore
from persistence.task_state_machine import TaskStatus
from persistence.trace_logger import TraceLogger


class PersistentPlannerAgent:
    """
    持久化多步骤规划 Agent
    基于 ReAct 模式，集成状态机、全链路埋点、步骤快照、断点恢复
    """

    def __init__(self, max_steps: int = 5):
        self.llm = LLMClient()
        self.tool_registry = ToolRegistry()
        self.tool_executor = ToolExecutor(
            self.tool_registry,
            max_retry=2,
            timeout=30
        )
        self.max_steps = max_steps
        self.system_prompt = """
你是 DevGuard 代码工程诊断助手。
你可以使用提供的工具来分析代码问题。

严格执行以下规则：
1.  任务分三步串行执行，每次只调用一个工具：
    第一步：调用 java_code_structure 统计代码结构信息
    第二步：调用 java_code_scan 扫描代码问题
    第三步：基于前两步的工具结果，输出完整的诊断报告和修复建议
2.  每个工具只调用一次，已经获取的结果直接使用，禁止重复调用相同工具
3.  所有结论必须基于工具返回的结果，禁止凭空编造问题
4.  工具返回结果开头会标记【工具执行成功】或【工具执行失败】，请根据标记判断执行状态
5.  如果工具执行失败，请把错误信息告知用户，不要编造结果

按步骤串行执行，不要并行，不要跳过，不要重复。
"""

    def run_by_id(self, task_id: int) -> str:
        """
        根据任务 ID 执行任务（支持断点恢复）
        """
        task = TaskStore.get_task(task_id)
        if not task:
            return f"任务不存在：{task_id}"

        # 状态校验：只有 PENDING / RUNNING 可以执行
        if task["status"] not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
            return f"任务状态为 {task['status']}，无法执行"

        start_time = time.time()

        # 只有 PENDING 状态的新任务，才更新为 RUNNING
        if task["status"] == TaskStatus.PENDING.value:
            TaskStore.update_status(task_id, TaskStatus.RUNNING.value)
            TraceLogger.task_start(task_id)
        else:
            print(f"[恢复] 任务 {task_id} 处于 RUNNING 状态，从中断点继续执行")
            TraceLogger.log(task_id, "TASK_RECOVER", "任务从中断点恢复执行")

        # 重建对话历史
        messages = self._rebuild_messages(task)
        tool_defs = self.tool_registry.get_tool_definitions()

        # 计算从第几步开始
        success_steps = TaskStore.list_success_steps(task_id)
        start_step = len(success_steps)

        total_steps = 0
        try:
            # ReAct 循环
            for step in range(start_step, self.max_steps):
                step_num = step + 1
                total_steps = step_num

                print(f"\n[Agent] 第 {step_num} 步推理中...")
                TraceLogger.reasoning_start(task_id, step_num, len(messages))

                # 1. 调用大模型思考
                try:
                    response = self.llm.chat_with_function(messages, tool_defs)
                except Exception as e:
                    raise Exception(f"大模型调用失败：{str(e)}")

                # 2. 不需要调用工具 = 任务完成
                if not response.get("tool_calls"):
                    print("[Agent] 任务完成，生成最终报告")
                    result = response.get("content", "生成失败")

                    duration_ms = int((time.time() - start_time) * 1000)
                    TaskStore.update_status(
                        task_id, TaskStatus.SUCCESS.value,
                        output=result,
                        total_steps=total_steps,
                        duration_ms=duration_ms
                    )
                    TraceLogger.task_success(task_id, total_steps, duration_ms)
                    return result

                # 3. 取出第一个工具调用（串行执行，一次一个）
                tool_call = response["tool_calls"][0]
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except Exception as e:
                    raise Exception(f"工具指令解析失败：{str(e)}")

                print(f"[Agent] 调用工具：{tool_name}")
                TraceLogger.tool_call_start(task_id, step_num, tool_name)

                tool_start = time.time()
                tool_result = self.tool_executor.execute(tool_name, arguments)
                success = "【工具执行成功】" in tool_result
                tool_duration = int((time.time() - tool_start) * 1000)
                TraceLogger.tool_call_end(task_id, step_num, tool_name, success, tool_duration)
                print(f"[Agent] 工具 {tool_name} 执行完成")

                # 4. 把 assistant 消息和 tool 消息加入历史（ID 严格对齐）
                messages.append({
                    "role": "assistant",
                    "content": response["content"],
                    "tool_calls": response["tool_calls"]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(tool_result)
                })

                # 5. 保存本步骤快照
                TaskStore.add_step(
                    task_id, step_num, "tool_call",
                    tool_name=tool_name,
                    input_snapshot=json.dumps([tool_call], ensure_ascii=False)
                )
                TaskStore.update_step_success(
                    task_id, step_num,
                    output_snapshot=str(tool_result),
                    duration_ms=tool_duration
                )

            # 超过最大步数
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"任务执行超过最大步数限制（{self.max_steps}步）"
            TaskStore.update_status(
                task_id, TaskStatus.FAILED.value,
                error_msg=error_msg,
                total_steps=total_steps,
                duration_ms=duration_ms
            )
            TraceLogger.task_fail(task_id, error_msg, duration_ms)
            return error_msg

        except Exception as e:
            # 全局异常捕获，标记任务失败
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            TaskStore.update_status(
                task_id, TaskStatus.FAILED.value,
                error_msg=error_msg,
                total_steps=total_steps,
                duration_ms=duration_ms
            )
            TraceLogger.task_fail(task_id, error_msg, duration_ms)
            return f"任务执行失败：{error_msg}"

    def run_new_task(self, input_text: str, task_type: str = "code_diagnose") -> str:
        """
        创建新任务并执行
        """
        task_id = TaskStore.create_task(task_type, input_text, self.max_steps)
        TraceLogger.task_create(task_id, input_text)
        print(f"[Agent] 任务已创建，ID：{task_id}")
        return self.run_by_id(task_id)

    # def _rebuild_messages(self, task: dict) -> list:
    #     """
    #     根据历史步骤重建对话上下文（断点恢复核心）
    #     严格对齐 tool_call_id，避免接口格式错误
    #     """
    #     messages = [
    #         {"role": "system", "content": self.system_prompt},
    #         {"role": "user", "content": task["input"]}
    #     ]

    #     steps = TaskStore.list_success_steps(task["id"])
    #     for step in steps:
    #         if not step["input_snapshot"] or not step["output_snapshot"]:
    #             continue

    #         try:
    #             tool_calls = json.loads(step["input_snapshot"])
    #             tool_call = tool_calls[0]
    #             # 还原 assistant 消息
    #             messages.append({
    #                 "role": "assistant",
    #                 "content": "",
    #                 "tool_calls": tool_calls
    #             })
    #             # 还原 tool 消息，ID 用真实的 tool_call.id
    #             messages.append({
    #                 "role": "tool",
    #                 "tool_call_id": tool_call["id"],
    #                 "content": step["output_snapshot"]
    #             })
    #         except Exception as e:
    #             print(f"[警告] 步骤 {step['step_num']} 还原失败：{str(e)}")
    #             continue

    #     return messages


    def _rebuild_messages(self, task: dict) -> list:
        """
        根据历史步骤重建对话上下文（断点恢复核心）
        严格对齐 tool_call_id，保证数量匹配
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task["input"]}
        ]

        steps = TaskStore.list_success_steps(task["id"])
        for step in steps:
            if not step["input_snapshot"] or not step["output_snapshot"]:
                continue

            try:
                tool_calls = json.loads(step["input_snapshot"])
                if not tool_calls:
                    continue
                    
                # 只取第一个工具调用（串行模式，一步一个）
                tool_call = tool_calls[0]
                
                # 还原 assistant 消息
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call]
                })
                # 还原 tool 消息，ID 和工具调用严格一致
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": step["output_snapshot"]
                })
            except Exception as e:
                print(f"[警告] 步骤 {step['step_num']} 还原失败：{str(e)}")
                continue

        return messages




    @staticmethod
    def recover_running_tasks():
        """
        进程启动时恢复所有中断的任务
        扫描 RUNNING 状态的任务，逐个继续执行
        """
        running_tasks = TaskStore.list_running_tasks()
        if not running_tasks:
            print("[恢复] 没有需要恢复的任务")
            return

        print(f"[恢复] 发现 {len(running_tasks)} 个中断任务，开始恢复...")
        agent = PersistentPlannerAgent()
        for task in running_tasks:
            print(f"[恢复] 继续执行任务 {task['id']}")
            result = agent.run_by_id(task["id"])
            print(f"\n[恢复] 任务 {task['id']} 执行结果：\n{result}\n")

