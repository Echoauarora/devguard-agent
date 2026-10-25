# import os
# import sys
# # ========== 数据库配置 ==========
# os.environ["DB_HOST"] = "127.0.0.1"
# os.environ["DB_PORT"] = "3306"
# os.environ["DB_USER"] = "root"
# os.environ["DB_PASSWORD"] = "7299018"  # 改成你的密码
# os.environ["DB_NAME"] = "devguard"

# # ========== 大模型配置 ==========
# os.environ["LLM_API_KEY"] = "sk-62b76670831b419eb7ad26626eb1c491"
# os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
# os.environ["LLM_MODEL"] = "deepseek-flash"

# import json
# import time
# from llm.llm_client import LLMClient
# from tools.tool_registry import ToolRegistry
# from tools.tool_executor import ToolExecutor
# from persistence.task_store import TaskStore
# from persistence.task_state_machine import TaskStatus
# from persistence.trace_logger import TraceLogger

# if __name__ == "__main__":
#     test_code = """
# public class Test {
#     private static final String PASSWORD = "123456";
    
#     public void query(String id) {
#         String sql = "select * from user where id=" + id;
#         System.out.println(sql);
        
#         if(id.equals("admin")) {
#             System.out.println("is admin");
#         }
#     }
# }
#     """
#     user_input = f"帮我全面诊断这段Java代码，先统计代码结构信息，再扫描所有问题，最后给出完整的修复报告：\n{test_code}"

#     # 1. 创建任务
#     task_id = TaskStore.create_task("code_diagnose", user_input, max_steps=5)
#     TraceLogger.task_create(task_id, user_input)
#     print(f"[模拟崩溃] 任务已创建，ID：{task_id}")

#     # 2. 标记任务开始执行
#     TaskStore.update_status(task_id, TaskStatus.RUNNING.value)
#     TraceLogger.task_start(task_id)

#     # 3. 初始化组件
#     llm = LLMClient()
#     tool_registry = ToolRegistry()
#     tool_executor = ToolExecutor(tool_registry, max_retry=2, timeout=30)
#     tool_defs = tool_registry.get_tool_definitions()

#     # 4. 构建初始消息
#     messages = [
#         {"role": "system", "content": "你是 DevGuard 代码工程诊断助手。按步骤执行：先统计结构，再扫描问题，最后输出报告。每个工具只调用一次。"},
#         {"role": "user", "content": user_input}
#     ]

#     # 5. 执行第一步推理 + 工具调用
#     print("[模拟崩溃] 执行第 1 步推理...")
#     response = llm.chat_with_function(messages, tool_defs)

#     # 执行第一个工具（结构统计）
#     tool_call = response["tool_calls"][0]
#     tool_name = tool_call["function"]["name"]
#     arguments = json.loads(tool_call["function"]["arguments"])
#     print(f"[模拟崩溃] 调用工具：{tool_name}")
    
#     tool_result = tool_executor.execute(tool_name, arguments)
#     print(f"[模拟崩溃] 工具 {tool_name} 执行完成")

#     # 6. 保存第一步步骤快照（模拟正常执行完第一步）
#     TaskStore.add_step(
#         task_id, 1, "tool_call",
#         tool_name=tool_name,
#         input_snapshot=json.dumps(response["tool_calls"], ensure_ascii=False)
#     )
#     TaskStore.update_step_success(task_id, 1, str(tool_result), duration_ms=1000)

#     print(f"[模拟崩溃] 第一步执行完成，任务状态保持 RUNNING，现在强制退出进程，模拟崩溃...")
    
#     # 7. 强制退出，不标记失败，模拟进程意外崩溃
#     sys.exit(1)
import os
import sys
# ========== 数据库配置 ==========
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "root"
os.environ["DB_PASSWORD"] = "7299018"  # 改成你的密码
os.environ["DB_NAME"] = "devguard"

# ========== 大模型配置 ==========
os.environ["LLM_API_KEY"] = "sk-62b76670831b419eb7ad26626eb1c491"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL"] = "deepseek-flash"

import json
import time
from llm.llm_client import LLMClient
from tools.tool_registry import ToolRegistry
from tools.tool_executor import ToolExecutor
from persistence.task_store import TaskStore
from persistence.task_state_machine import TaskStatus
from persistence.trace_logger import TraceLogger

if __name__ == "__main__":
    test_code = """
public class Test {
    private static final String PASSWORD = "123456";
    
    public void query(String id) {
        String sql = "select * from user where id=" + id;
        System.out.println(sql);
        
        if(id.equals("admin")) {
            System.out.println("is admin");
        }
    }
}
    """
    user_input = f"帮我全面诊断这段Java代码，先统计代码结构信息，再扫描所有问题，最后给出完整的修复报告：\n{test_code}"

    # 1. 创建任务
    task_id = TaskStore.create_task("code_diagnose", user_input, max_steps=5)
    TraceLogger.task_create(task_id, user_input)
    print(f"[模拟崩溃] 任务已创建，ID：{task_id}")

    # 2. 标记任务开始执行
    TaskStore.update_status(task_id, TaskStatus.RUNNING.value)
    TraceLogger.task_start(task_id)

    # 3. 初始化组件（和正式Agent完全一致）
    llm = LLMClient()
    tool_registry = ToolRegistry()
    tool_executor = ToolExecutor(tool_registry, max_retry=2, timeout=30)
    tool_defs = tool_registry.get_tool_definitions()

    system_prompt = """
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

    # 4. 构建初始消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    # 5. 执行第一步推理 + 串行取第一个工具
    print("[模拟崩溃] 执行第 1 步推理...")
    response = llm.chat_with_function(messages, tool_defs)

    # 只取第一个工具调用（和正式Agent逻辑一致）
    tool_call = response["tool_calls"][0]
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    print(f"[模拟崩溃] 调用工具：{tool_name}")
    
    tool_result = tool_executor.execute(tool_name, arguments)
    print(f"[模拟崩溃] 工具 {tool_name} 执行完成")

    # 6. 保存第一步步骤快照（只存当前这一个工具调用，一一对应）
    TaskStore.add_step(
        task_id, 1, "tool_call",
        tool_name=tool_name,
        input_snapshot=json.dumps([tool_call], ensure_ascii=False)
    )
    TaskStore.update_step_success(task_id, 1, str(tool_result), duration_ms=1000)

    print(f"[模拟崩溃] 第一步执行完成，任务状态保持 RUNNING，现在强制退出进程，模拟崩溃...")
    
    # 7. 强制退出
    sys.exit(1)
