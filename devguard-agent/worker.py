import sys
import os
import time
import json
import uuid
import threading
import concurrent.futures
import urllib.request
import traceback

try:
    import redis
except ImportError:
    redis = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient
from tools.tool_registry import ToolRegistry

BACKEND_BASE = os.getenv("BACKEND_BASE", "http://localhost:8080/api")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))
MAX_STEPS_PER_TASK = int(os.getenv("MAX_STEPS", "10"))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
LOCK_TTL_SEC = int(os.getenv("LOCK_TTL", "30"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
WORKER_ID = "worker-" + uuid.uuid4().hex[:8]

LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0
MAX_TOOL_RESULT_LEN = 2000
MAX_MESSAGES_BEFORE_COMPRESS = 30
TOOL_RETRY_COUNT = 2          # Group 5: 工具异常重试次数
TOOL_TIMEOUT_SEC = 30         # Group 20: 慢工具隔离超时
TOKEN_COST_THRESHOLD = 50000  # Group 7: 单任务累计tokens熔断阈值

registry = ToolRegistry()

redis_client = None
if redis:
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        redis_client.ping()
    except Exception:
        redis_client = None

llm = None
try:
    llm = LLMClient()
except Exception:
    pass

PROJECT_SYSTEM_PROMPT = (
    "你是 DevGuard，一个专业的 Java/Go/Python 工程级代码安全与质量分析 Agent。\n"
    "\n"
    "## 角色\n"
    "- 你必须先用 project_list_files 了解工程全貌，然后选择关键文件读取分析。\n"
    "- 绝对不能跳过工具直接输出结论。\n"
    "\n"
    "## 工程探索策略\n"
    "- Step 1: 调用 project_list_files 获取所有源码文件列表。\n"
    "- Step 2: 根据文件列表识别 Controller/Service/DAO 分层架构，选择入口文件（如 Controller）读取。\n"
    "- Step 3: 对每个读取到的源码文件，用 java_code_structure 和 java_code_scan 进行结构化分析。\n"
    "- Step 4: 重点关注跨文件漏洞链（如 Controller 输入 → Service SQL 拼接）。\n"
    "- 不要一次性读取所有文件！按需读取，优先读取高风险模块。\n"
    "\n"
    "## 输出格式\n"
    "最终报告请严格按以下 JSON 格式输出（不要加 markdown 代码块标记）：\n"
    "{\n"
    "  \"summary\": \"工程整体安全评价（100字以内）\",\n"
    "  \"architecture\": \"架构分析（分层、依赖关系、技术栈）\",\n"
    "  \"issues\": [\n"
    "    {\"severity\": \"HIGH|MEDIUM|LOW\", \"type\": \"SQL注入|硬编码|...\", \"file\": \"文件路径\", \"detail\": \"具体问题描述\", \"suggestion\": \"修复建议\"}\n"
    "  ],\n"
    "  \"fileCount\": 0,\n"
    "  \"overallScore\": 85,\n"
    "  \"conclusion\": \"最终结论\"\n"
    "}"
)


SYSTEM_PROMPT = (
    "你是 DevGuard，一个专业的 Java 代码安全与质量分析 Agent。\n"
    "\n"
    "## 输入校验规则（最高优先级）\n"
    "- 收到用户代码后，先用 java_code_structure 检查代码是否真的是 Java 源码。\n"
    "- 如果输入是纯数字、乱码、或无法识别的内容（没有 package/class/import/public/void 等 Java 关键词），"
    "直接在最终报告的 summary 里写明「输入不是有效的 Java 代码」，issues 为空，不要编造任何分析结果。\n"
    "- 绝对不能对无效输入编造漏洞、类名、行号。\n"
    "\n"
    "## 角色\n"
    "- 你必须先用工具收集代码信息，再基于工具结果输出分析报告。\n"
    "- 绝对不能跳过工具直接输出结论。\n"
    "\n"
    "## 工具使用策略\n"
    "- 第一步必须调用至少一个工具（java_code_structure 或 java_code_scan）。\n"
    "- 推荐在 Step 1 同时调用 java_code_structure（看代码全貌）和 java_code_scan（找漏洞）。\n"
    "- 拿到工具结果后，再决定是否需要进一步探查。\n"
    "- 最终要综合所有工具结果，输出一份结构化的分析报告。\n"
    "\n"
    "## 输出格式\n"
    "最终报告请严格按以下 JSON 格式输出（不要加 markdown 代码块标记）：\n"
    "{\n"
    "  \"summary\": \"100字以内的代码整体评价\",\n"
    "  \"issues\": [\n"
    "    {\"severity\": \"HIGH|MEDIUM|LOW\", \"type\": \"SQL注入|硬编码|...\", \"detail\": \"具体问题描述\", \"suggestion\": \"修复建议\"}\n"
    "  ],\n"
    "  \"metrics\": {\"totalLines\": 0, \"effectiveLines\": 0, \"classCount\": 0, \"methodCount\": 0},\n"
    "  \"overallScore\": 85,\n"
    "  \"conclusion\": \"最终结论\"\n"
    "}"
)


def api_get(path):
    try:
        resp = urllib.request.urlopen(BACKEND_BASE + path, timeout=10)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def api_post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            BACKEND_BASE + path, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        print("[HTTP POST ERR] " + path + ": " + str(e))
        return None


JAVA_KEYWORDS = [
    "package ", "import ", "public class", "private class", "protected class",
    "class ", "interface ", "enum ", "extends ", "implements ",
    "public void", "private void", "protected void",
    "public static", "public final", "static final",
    "public String", "public int", "public long", "public boolean",
    "@Override", "@Test", "@Service", "@Controller", "@Repository",
    "System.out.println", "String ", "int ", "boolean ", "new ",
    "return ", "throw ", "try {", "catch ", "finally {",
    "if (", "for (", "while (", "switch (",
    "void ", "String ", "Integer ", "Long ", "List<", "Map<",
    "@RestController", "@RequestMapping", "@PostMapping", "@GetMapping",
    "jdbc:", "DriverManager", "Connection", "Statement", "ResultSet",
    "PreparedStatement",
]


def is_valid_java_code(code):
    if not code or not code.strip():
        return False, "输入为空"
    stripped = code.strip()
    if len(stripped) < 15:
        return False, "输入过短（<15字符），不足以构成有效Java源码"
    keyword_hits = sum(1 for kw in JAVA_KEYWORDS if kw in stripped)
    if keyword_hits < 2:
        import re
        digit_ratio = len(re.findall(r'\d', stripped)) / max(len(stripped), 1)
        if digit_ratio > 0.7:
            return False, "输入看起来是纯数字，不是Java代码"
        return False, "未检测到足够的Java语法关键词（仅命中%d个）" % keyword_hits
    return True, ""


def trace(task_id, step_num, event_type, event_detail="", duration_ms=None, extra=None):
    try:
        api_post("/trace/log", {
            "taskId": task_id, "stepNum": step_num,
            "eventType": event_type,
            "eventDetail": str(event_detail)[:5000] if event_detail else "",
            "durationMs": duration_ms,
            "extra": json.dumps(extra, ensure_ascii=False)[:5000] if extra else None
        })
    except Exception:
        pass


# Group 12: 锁降级 - Redis 不可用时走本地内存锁
import threading
import concurrent.futures
_local_locks = {}
_local_lock_guard = threading.Lock()
_redis_lock_available = True
_redis_lock_fail_count = 0

def _get_local_lock(task_id):
    with _local_lock_guard:
        if task_id not in _local_locks:
            _local_locks[task_id] = threading.Event()
        return _local_locks[task_id]

def try_acquire_lock(task_id):
    global _redis_lock_available, _redis_lock_fail_count
    # Group 12a: 降级中 → 本地内存锁
    if not redis_client or not _redis_lock_available:
        lock = _get_local_lock(task_id)
        acquired = not lock.is_set()
        if acquired:
            lock.set()
            print("  [LOCK-LOCAL] acquired task #" + str(task_id))
            trace(task_id, 0, "LOCK_ACQUIRED_DEGRADED", "worker=" + WORKER_ID)
        else:
            print("  [LOCK-LOCAL] FAILED task #" + str(task_id) + " (held locally)")
        return acquired

    lock_key = "devguard:task:lock:" + str(task_id)
    try:
        ok = redis_client.set(lock_key, WORKER_ID, nx=True, ex=LOCK_TTL_SEC)
        _redis_lock_fail_count = 0  # 成功 → 重置计数
        _redis_lock_available = True
        if ok:
            print("  [LOCK] acquired task #" + str(task_id) + " by " + WORKER_ID)
            trace(task_id, 0, "LOCK_ACQUIRED", "worker=" + WORKER_ID)
        else:
            owner = redis_client.get(lock_key)
            print("  [LOCK] FAILED task #" + str(task_id) + ", owner=" + str(owner))
        return bool(ok)
    except Exception as e:
        # Group 12b: Redis 异常 → 累加失败计数，达3次切降级
        _redis_lock_fail_count += 1
        print("  [LOCK][WARN] Redis fail=" + str(_redis_lock_fail_count) + ": " + str(e)[:80])
        if _redis_lock_fail_count >= 3:
            _redis_lock_available = False
            print("  [LOCK] REDIS LOCK DEGRADED → switching to local-memory")
        # 降级路径：本地锁兜底
        lock = _get_local_lock(task_id)
        if not lock.is_set():
            lock.set()
            return True
        return False


def release_lock(task_id):
    # Group 12: 降级时释放本地锁
    if not redis_client or not _redis_lock_available:
        lock = _local_locks.get(task_id)
        if lock:
            lock.clear()
            print("  [LOCK-LOCAL] released task #" + str(task_id))
        return
    try:
        lock_key = "devguard:task:lock:" + str(task_id)
        if redis_client.get(lock_key) == WORKER_ID:
            redis_client.delete(lock_key)
            print("  [LOCK] released task #" + str(task_id))
    except Exception:
        lock = _local_locks.get(task_id)
        if lock: lock.clear()


def renew_lock(task_id):
    if not redis_client:
        return
    lock_key = "devguard:task:lock:" + str(task_id)
    if redis_client.get(lock_key) == WORKER_ID:
        redis_client.expire(lock_key, LOCK_TTL_SEC)


_hb_task = None
_hb_stop = threading.Event()


def _hb_loop():
    while not _hb_stop.is_set():
        if _hb_task is not None:
            renew_lock(_hb_task)
        _hb_stop.wait(HEARTBEAT_INTERVAL)


def start_heartbeat(tid):
    global _hb_task, _hb_stop
    _hb_task = tid
    _hb_stop.clear()
    threading.Thread(target=_hb_loop, daemon=True).start()


def stop_heartbeat():
    global _hb_task, _hb_stop
    _hb_stop.set()
    _hb_task = None


def recover_running_tasks():
    """Group 19: 并发恢复竞争 - 用 recover:lock:{tid} SET NX EX 保证只有一个Worker接管"""
    if not redis_client:
        return
    print("[WORKER] checking crashed RUNNING tasks...")
    try:
        resp = api_get("/task/running")
        if not resp or resp.get("code") != 200:
            return
        recovered = 0
        for task in resp.get("data", []):
            tid = task["id"]
            lock_key = "devguard:task:lock:" + str(tid)
            ttl = redis_client.ttl(lock_key)
            if ttl == -2 or (ttl > 0 and ttl < 5):
                # Group 19: 竞争恢复锁（30秒TTL，防止多Worker同时接管）
                recover_lock = "devguard:recover:lock:" + str(tid)
                got = redis_client.set(recover_lock, WORKER_ID, nx=True, ex=30)
                if not got:
                    print("  [RECOVER] task #" + str(tid) + " already being recovered by another worker, skip")
                    continue
                print("  [RECOVER] task #" + str(tid) + " ttl=" + str(ttl) + "s, " + WORKER_ID + " took over")
                api_post("/task/" + str(tid) + "/status", {"status": "PENDING"})
                recovered += 1
        print("[WORKER] recover done, took over " + str(recovered) + " tasks")
    except Exception as e:
        print("[WORKER][WARN] recovery failed: " + str(e))


def call_llm_with_retry(messages, tools, task_id, step_num):
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            response = llm.chat_with_function(messages, tools)
            # Group 7: Token 成本累计 + 熔断
            usage = getattr(response, "usage", None)
            if usage and getattr(usage, "total_tokens", 0):
                global accumulated_tokens
                accumulated_tokens += usage.total_tokens
                if accumulated_tokens > TOKEN_COST_THRESHOLD:
                    trace(task_id, step_num, "TOKEN_BUDGET_EXCEEDED",
                          "tokens=" + str(accumulated_tokens) + " > " + str(TOKEN_COST_THRESHOLD))
                    final_payload = {"status": "FAILED",
                        "resultSummary": "TOKEN_BUDGET_EXCEEDED: tokens=" + str(accumulated_tokens)}
                    api_post("/task/" + str(task_id) + "/status", final_payload)
                    trace(task_id, step_num, "TASK_END", "FAILED(token_exceeded)")
                    print("  [ReAct] task #" + str(task_id) + " FAILED: token budget exceeded", flush=True)
                    return None, "TOKEN_BUDGET_EXCEEDED"
            return response, None
        except Exception as e:
            print("  [LLM RETRY " + str(attempt) + "/" + str(LLM_MAX_RETRIES) + "] " + str(e)[:120])
            trace(task_id, step_num, "LLM_RETRY",
                  "attempt=" + str(attempt) + "/" + str(LLM_MAX_RETRIES) + " err=" + str(e)[:200])
            if attempt < LLM_MAX_RETRIES:
                delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)
            else:
                return None, str(e)


def compress_messages(messages):
    if len(messages) <= MAX_MESSAGES_BEFORE_COMPRESS:
        return messages
    system = messages[0]

    split_idx = len(messages) - 1
    while split_idx > 1:
        m = messages[split_idx]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            break
        split_idx -= 1
    split_idx = max(split_idx, len(messages) - 8)

    recent = messages[split_idx:]
    old = messages[1:split_idx]

    if not old:
        return messages

    summary_parts = []
    for m in old:
        role = m.get("role", "?")
        content = str(m.get("content", ""))[:150]
        if role == "assistant" and m.get("tool_calls"):
            tc_names = [tc["function"]["name"] for tc in m["tool_calls"]]
            summary_parts.append("  - [assistant] called tools: " + ", ".join(tc_names))
        elif role == "tool":
            summary_parts.append("  - [tool:" + m.get("name", "?") + "] -> " + content)
        elif role == "assistant":
            summary_parts.append("  - [assistant] (final): " + content)
        elif role == "user":
            summary_parts.append("  - [user]: " + content)
        else:
            summary_parts.append("  - " + role + ": " + content)

    summary = (
        "[CONTEXT SUMMARY - 历史对话压缩]\n"
        "以下是之前步骤的摘要，不是完整消息。请结合最近的完整消息继续推理。\n"
        + "\n".join(summary_parts)
        + "\n[/CONTEXT SUMMARY]"
    )

    return [system, {"role": "user", "content": summary}] + recent


def truncate_tool_result(result):
    s = str(result)
    if len(s) <= MAX_TOOL_RESULT_LEN:
        return s
    half = MAX_TOOL_RESULT_LEN // 2
    return s[:half] + "\n...[TRUNCATED total=" + str(len(s)) + "]...\n" + s[-half:]


def is_empty_tool_result(result):
    s = str(result).strip()
    if not s:
        return True
    if s in ("[]", "{}", "None", "null"):
        return True
    if len(s) < 5:
        return True
    if "【工具执行失败】" in s or "[TOOL ERROR]" in s:
        return True
    return False


def process_task_react(task):
    task_id = task["id"]
    input_type = task.get("taskInputType", "snippet") or "snippet"
    code = task.get("input", "")
    max_steps = max(5, task.get("maxSteps", 8)) if input_type == "zip_project" else max(3, task.get("maxSteps", 5))
    start_time = time.time()

    project_mode = (input_type == "zip_project")
    if project_mode:
        registry.task_id = task_id
        registry.backend_base = BACKEND_BASE
    else:
        valid, reason = is_valid_java_code(code)
        if not valid:
            print("  [VALIDATE] input rejected: " + reason, flush=True)
            trace(task_id, 0, "INPUT_REJECTED", reason)
            api_post("/task/" + str(task_id) + "/status", {
                "status": "FAILED",
                "output": "",
                "errorMsg": "输入无效：" + reason + "（请粘贴有效的 Java 代码片段）",
                "totalSteps": 0,
                "durationMs": int((time.time() - start_time) * 1000)
            })
            return

    api_post("/task/" + str(task_id) + "/status", {"status": "RUNNING"})
    trace(task_id, 0, "TASK_START", "type=" + str(task.get("taskType")) + ", inputType=" + input_type,
          extra={"input_preview": code[:200], "max_steps": max_steps, "project_mode": project_mode})

    steps_resp = api_get("/task/" + str(task_id) + "/steps")
    existing_steps = steps_resp.get("data", []) if steps_resp else []
    active_prompt = PROJECT_SYSTEM_PROMPT if project_mode else SYSTEM_PROMPT
    messages = [{"role": "system", "content": active_prompt}]
    if existing_steps:
        trace(task_id, 0, "RESUME", "existing steps=" + str(len(existing_steps)))
    else:
        if project_mode:
            messages.append({"role": "user", "content": "请先用 project_list_files 了解工程全貌，然后选择关键文件读取分析。"})
        else:
            messages.append({"role": "user", "content": "以下是待分析的 Java 代码：\n\n```java\n" + code + "\n```\n\n请开始分析。"})

    step_num = len(existing_steps) + 1
    final_output = None
    total_tool_calls = 0
    has_called_any_tool = False
    expand_count = 0
    force_hint_count = 0
    last_tool_signature = None
    stagnant_steps = 0
    tool_sequence = []
    BASE_MAX = max_steps
    TOTAL_CAP = BASE_MAX + 6

    while True:
        if step_num > max_steps:
            is_effective = stagnant_steps < 2 and expand_count < 2 and max_steps < TOTAL_CAP
            if is_effective:
                max_steps += 3
                expand_count += 1
                print("  [ReAct] Adaptive expand +3 (now " + str(max_steps) + ", total_expand=" + str(expand_count) + ")", flush=True)
                trace(task_id, step_num, "ADAPTIVE_EXPAND",
                      "+3 steps (effective推进, stagnant=" + str(stagnant_steps) + ")")
            else:
                print("  [ReAct] Hit hard limit (steps=" + str(step_num) + ", cap=" + str(TOTAL_CAP) + ", stagnant=" + str(stagnant_steps) + ")", flush=True)
                break
        messages = compress_messages(messages)

        print("  [ReAct Step " + str(step_num) + "] LLM thinking...", flush=True)
        llm_start = time.time()
        trace(task_id, step_num, "LLM_REASONING_START", "messages=" + str(len(messages)))

        response, llm_err = call_llm_with_retry(
            messages, registry.get_tool_definitions(project_mode=project_mode), task_id, step_num)

        if llm_err:
            print("  [LLM FATAL] " + llm_err)
            trace(task_id, step_num, "LLM_FATAL_ERROR", llm_err)
            print("  [FALLBACK] LLM unavailable, falling back to Static scan...", flush=True)
            trace(task_id, step_num, "LLM_FALLBACK_STATIC", llm_err)
            process_task_static(task)
            return

        llm_dur = int((time.time() - llm_start) * 1000)
        tool_calls = response.get("tool_calls") or []
        assistant_msg = {
            "role": "assistant",
            "content": response.get("content", "") or ""
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        trace(task_id, step_num, "LLM_REASONING_END",
              response.get("content", "")[:1000],
              duration_ms=llm_dur,
              extra={"tool_call_count": len(tool_calls)})

        if not tool_calls:
            if not has_called_any_tool:
                force_hint_count += 1
                if force_hint_count >= 3:
                    print("  [ReAct] AGENT_LLM_MALFORMED: forced tool call " + str(force_hint_count) + " times, still no tool_calls. FAILED.", flush=True)
                    trace(task_id, step_num, "AGENT_LLM_MALFORMED",
                          "LLM连续" + str(force_hint_count) + "次未按规范调用工具")
                    duration_ms = int((time.time() - start_time) * 1000)
                    api_post("/task/" + str(task_id) + "/status", {
                        "status": "FAILED",
                        "errorCode": "AGENT_LLM_MALFORMED",
                        "errorMsg": "LLM连续" + str(force_hint_count) + "次未按规范调用工具，已强制终止",
                        "durationMs": duration_ms,
                        "totalSteps": step_num - 1
                    })
                    return
                print("  [ReAct] NO tool_calls yet, forcing tool usage (hint#" + str(force_hint_count) + ", step=" + str(step_num) + ")...", flush=True)
                trace(task_id, step_num, "FORCE_TOOL_CALL",
                      "no tool called yet, hint#" + str(force_hint_count))
                messages.append({
                    "role": "user",
                    "content": "警告：你还没有调用任何工具！你必须先用 java_code_structure 和 java_code_scan 收集代码信息，拿到工具返回结果后再输出分析报告。请现在就调用工具。"
                })
                step_num += 1
                continue
            final_output = response.get("content", "")
            print("  [ReAct] LLM final report", flush=True)
            break

        current_tool_sig = None
        if tool_calls:
            sig_parts = []
            for tc in tool_calls:
                fn = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except Exception:
                    args = {}
                sig_parts.append(fn + ":" + str(sorted(args.keys())))
            current_tool_sig = "|".join(sig_parts)

        if current_tool_sig == last_tool_signature:
            stagnant_steps += 1
        else:
            stagnant_steps = 0
        last_tool_signature = current_tool_sig

        if current_tool_sig:
            tool_sequence.append(current_tool_sig)
            if len(tool_sequence) > 8:
                tool_sequence.pop(0)

            if len(tool_sequence) >= 4:
                recent = tool_sequence[-4:]
                if len(set(recent)) <= 2 and recent[0] == recent[2] and recent[1] == recent[3]:
                    print("  [ReAct] AGENT_LOOP_DETECTED: " + str(recent) + " -> terminating", flush=True)
                    trace(task_id, step_num, "AGENT_LOOP_DETECTED",
                          "loop pattern=" + str(recent))
                    duration_ms = int((time.time() - start_time) * 1000)
                    api_post("/task/" + str(task_id) + "/status", {
                        "status": "FAILED",
                        "errorCode": "AGENT_LOOP_DETECTED",
                        "errorMsg": "检测到工具调用循环: " + " -> ".join(recent),
                        "durationMs": duration_ms,
                        "totalSteps": step_num - 1
                    })
                    return

        has_called_any_tool = True
        total_tool_calls += len(tool_calls)

        for tc in tool_calls:
            fname = tc["function"]["name"]
            fargs_str = tc["function"].get("arguments", "{}")
            try:
                fargs = json.loads(fargs_str)
            except Exception:
                fargs = {}

            if "code" not in fargs or not fargs["code"]:
                fargs["code"] = code

            print("  [ReAct] call tool: " + fname + " ...", flush=True)
            tool_start = time.time()
            trace(task_id, step_num, "TOOL_CALL", fname, extra={"arguments": fargs})

            add_r = api_post("/task/" + str(task_id) + "/step", {
                "stepNum": step_num, "stepType": "TOOL_CALL",
                "toolName": fname, "inputSnapshot": str(fargs)[:2000],
                "status": "RUNNING"
            })
            step_id = None
            if add_r and isinstance(add_r, dict):
                step_id = (add_r.get("data") or {}).get("id")

            # Group 20 + Group 5: ThreadPoolExecutor 隔离 + 异常重试
            raw_result = None
            tool_retry_result = None
            for _retry in range(TOOL_RETRY_COUNT + 1):
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _executor:
                    _future = _executor.submit(registry.execute_tool, fname, fargs)
                    try:
                        raw_result = _future.result(timeout=TOOL_TIMEOUT_SEC)
                        tool_retry_result = None
                        break
                    except concurrent.futures.TimeoutError:
                        tool_retry_result = "TIMEOUT(" + fname + ">" + str(TOOL_TIMEOUT_SEC) + "s)"
                        trace(task_id, step_num, "TOOL_TIMEOUT", fname + " attempt=" + str(_retry + 1),
                              extra={"seconds": TOOL_TIMEOUT_SEC})
                        raw_result = "[TOOL TIMEOUT] " + fname + " > " + str(TOOL_TIMEOUT_SEC) + "s"
                    except Exception as e:
                        tool_retry_result = str(e)
                        trace(task_id, step_num, "TOOL_ERROR", fname + " attempt=" + str(_retry + 1),
                              extra={"error": str(e)[:300]})
            if tool_retry_result is not None:
                if "TIMEOUT" in tool_retry_result or raw_result is None:
                    pass  # raw_result already set above
                else:
                    raw_result = "[TOOL ERROR] " + tool_retry_result

            result = truncate_tool_result(raw_result)
            tool_dur = int((time.time() - tool_start) * 1000)

            if step_id:
                api_post("/task/step/" + str(step_id), {
                    "status": "SUCCESS",
                    "outputSnapshot": str(raw_result)[:8000],
                    "durationMs": tool_dur
                })
            trace(task_id, step_num, "TOOL_RESULT", fname,
                  duration_ms=tool_dur,
                  extra={"preview": str(result)[:500], "empty": is_empty_tool_result(raw_result)})
            print("  [ReAct] " + fname + " -> OK (" + str(tool_dur) + "ms)", flush=True)

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "name": fname,
                "content": result
            }

            if is_empty_tool_result(raw_result):
                tool_msg["content"] = (
                    result + "\n\n[SYSTEM NOTICE] 工具返回为空或无有效结果。"
                    "请换一个工具或调整参数再试一次。"
                )

            messages.append(tool_msg)

        step_num += 1

    duration_ms = int((time.time() - start_time) * 1000)

    final_failed_reason = None
    if not final_output:
        if expand_count >= 2:
            final_failed_reason = "AGENT_STAGNANT"
            final_output = "分析未完成：Agent自适应步数扩容" + str(expand_count) + "次后仍停滞，检测到无有效推进。"
        elif step_num > TOTAL_CAP:
            final_failed_reason = "AGENT_STEP_EXCEEDED"
            final_output = "分析未完成：Agent达到最大步数上限" + str(TOTAL_CAP) + "步，未产出最终报告。"
        else:
            final_failed_reason = "AGENT_NO_FINAL"
            final_output = "分析未完成：Agent在" + str(step_num) + "步内未输出最终报告。"

    final_status = "SUCCESS" if not final_failed_reason else "FAILED"
    final_payload = {
        "status": final_status,
        "output": final_output,
        "durationMs": duration_ms,
        "totalSteps": step_num - 1
    }
    if final_failed_reason:
        final_payload["errorCode"] = final_failed_reason
    api_post("/task/" + str(task_id) + "/status", final_payload)
    trace(task_id, step_num, "TASK_FINISH", final_status, duration_ms=duration_ms,
          extra={"total_tool_calls": total_tool_calls, "total_steps": step_num - 1})
    print("  [ReAct] task #" + str(task_id) + " " + final_status +
          " (" + str(duration_ms) + "ms) tools=" + str(total_tool_calls) + "\n", flush=True)


def process_task_static(task):
    import time as _t
    task_id = task["id"]
    input_type = task.get("taskInputType", "snippet") or "snippet"
    code = task.get("input", "") or ""
    start_ms = int(_t.time() * 1000)

    if input_type != "zip_project":
        valid, reason = is_valid_java_code(code)
        if not valid:
            trace(task_id, 0, "INPUT_REJECTED", reason)
            api_post("/task/" + str(task_id) + "/status", {
                "status": "FAILED",
                "output": "",
                "errorMsg": "输入无效：" + reason + "（请粘贴有效的 Java 代码片段）",
                "totalSteps": 0,
                "durationMs": int(_t.time() * 1000) - start_ms
            })
            return

    api_post("/task/" + str(task_id) + "/status", {"status": "RUNNING"})

    file_count = 0
    project_tree = []
    if input_type == "zip_project":
        trace(task_id, 0, "TASK_START", "mode=Static(zip_project_read_all)")
        code_parts = []
        list_resp = api_get("/task/project/list-files?taskId=" + str(task_id))
        if isinstance(list_resp, dict):
            project_tree = list_resp.get("data", []) or []
        for fp in project_tree:
            if not fp.endswith('.java'):
                continue
            file_count += 1
            read_resp = api_get("/task/project/read-file?taskId=" + str(task_id) + "&filePath=" + fp)
            if isinstance(read_resp, dict):
                fc = read_resp.get("data", {}).get("content", "") if isinstance(read_resp.get("data"), dict) else ""
                if fc:
                    code_parts.append("// === FILE: " + fp + " ===\n" + fc)
        code = "\n\n".join(code_parts)
        if not code.strip():
            trace(task_id, 1, "ERROR", "zip_project no java files found")
            api_post("/task/" + str(task_id) + "/status", {
                "status": "FAILED",
                "output": "",
                "errorMsg": "工程内无 .java 源码文件",
                "totalSteps": 0,
                "durationMs": int(_t.time() * 1000) - start_ms
            })
            return
    else:
        trace(task_id, 0, "TASK_START", "mode=Static(structured_scan)")

    trace(task_id, 1, "TOOL_CALL", "java_code_scan", extra={"tool": "java_code_scan"})
    scan_issues = registry.java_code_scan(code)
    scan_ms = int(_t.time() * 1000)

    step_resp = api_post("/task/" + str(task_id) + "/step", {
        "stepNum": 1,
        "stepType": "TOOL_CALL",
        "toolName": "java_code_scan",
        "inputSnapshot": code[:1000],
        "outputSnapshot": json.dumps(scan_issues[:20], ensure_ascii=False)[:4000],
        "status": "SUCCESS",
        "durationMs": scan_ms - start_ms
    })
    step_id = None
    if isinstance(step_resp, dict):
        step_id = step_resp.get("id") or step_resp.get("stepId")
    trace(task_id, 1, "TOOL_RESULT", "java_code_scan",
          duration_ms=scan_ms - start_ms,
          extra={"issue_count": len(scan_issues)})

    structured = registry.java_code_structure(code)
    struct_ms = int(_t.time() * 1000)

    api_post("/task/" + str(task_id) + "/step", {
        "stepNum": 2,
        "stepType": "TOOL_CALL",
        "toolName": "java_code_structure",
        "inputSnapshot": code[:1000],
        "outputSnapshot": json.dumps(structured, ensure_ascii=False)[:2000],
        "status": "SUCCESS",
        "durationMs": struct_ms - scan_ms
    })

    final_ms = int(_t.time() * 1000)
    duration_ms = final_ms - start_ms

    high_count = 0
    med_count = 0
    low_count = 0
    for iss in scan_issues:
        sev = (iss.get("severity") or "").upper()
        if sev == "HIGH": high_count += 1
        elif sev == "MEDIUM": med_count += 1
        elif sev == "LOW": low_count += 1

    effective_lines = structured.get("metrics", {}).get("effectiveLines", 0) if isinstance(structured, dict) else 0
    class_count = structured.get("metrics", {}).get("classCount", 0) if isinstance(structured, dict) else 0
    method_count = structured.get("metrics", {}).get("methodCount", 0) if isinstance(structured, dict) else 0
    field_count = structured.get("metrics", {}).get("fieldCount", 0) if isinstance(structured, dict) else 0

    score = 100 - high_count * 20 - med_count * 8 - low_count * 2
    score = max(0, min(100, score))

    lines_of_code = structured.get("metrics", {}).get("totalLines", len(code.split("\n"))) if isinstance(structured, dict) else len(code.split("\n"))

    summary_parts = []
    summary_parts.append("安全评分: %d/100" % score)
    if input_type == "zip_project":
        summary_parts.append("工程: %d 个 .java 文件" % file_count)
    summary_parts.append("代码规模: %d 类 %d 方法 %d 行有效代码" % (class_count, method_count, effective_lines))
    summary_parts.append("发现问题: HIGH=%d MEDIUM=%d LOW=%d" % (high_count, med_count, low_count))
    result_summary = " | ".join(summary_parts)

    lines = []
    lines.append("# 代码安全分析报告")
    lines.append("")

    if input_type == "zip_project":
        lines.append("## 工程概览")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append("| 工程类型 | ZIP 工程扫描 |")
        lines.append("| Java 文件数 | %d" % file_count)
        lines.append("| 代码总行数 | %d" % lines_of_code)
        lines.append("| 有效代码行 | %d" % effective_lines)
        lines.append("| 类数量 | %d" % class_count)
        lines.append("| 方法数量 | %d" % method_count)
        lines.append("| 字段数量 | %d" % field_count)
        lines.append("")
        lines.append("**工程文件清单：**")
        lines.append("")
        for fp in project_tree:
            icon = "🔴" if "dao" in fp.lower() or "DB" in fp or "db" in fp else ("🟡" if "ui" in fp.lower() else "📄")
            lines.append("- %s `%s`" % (icon, fp))
        lines.append("")
    else:
        lines.append("## 代码概览")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append("| 扫描模式 | 单片段扫描 |")
        lines.append("| 代码总行数 | %d" % lines_of_code)
        lines.append("| 有效代码行 | %d" % effective_lines)
        lines.append("| 类数量 | %d" % class_count)
        lines.append("| 方法数量 | %d" % method_count)
        lines.append("")

    lines.append("## 安全评分: %d/100" % score)
    lines.append("")
    if score >= 80:
        lines.append("🟢 代码整体安全状况良好，可按建议逐项优化。")
    elif score >= 50:
        lines.append("🟡 存在一定安全隐患，建议尽快修复中等和高危问题。")
    else:
        lines.append("🔴 存在严重安全漏洞，必须立即修复后才能投入生产！")
    lines.append("")
    lines.append("| 严重级别 | 数量 | 建议 |")
    lines.append("|----------|------|------|")
    lines.append("| 🔴 HIGH | %d | 必须立即修复 |" % high_count)
    lines.append("| 🟠 MEDIUM | %d | 建议近期修复 |" % med_count)
    lines.append("| 🟡 LOW | %d | 建议优化改善 |" % low_count)
    lines.append("")

    if scan_issues:
        lines.append("## 问题详情")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, iss in enumerate(scan_issues, 1):
            sev = (iss.get("severity") or "").upper()
            sev_icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡", "ERROR": "❌"}.get(sev, "⚪")
            sev_label = {"HIGH": "高危", "MEDIUM": "中等", "LOW": "低危", "ERROR": "错误"}.get(sev, sev)
            issue_type = iss.get("type", "UNKNOWN")
            line_num = iss.get("line", "?")
            detail = iss.get("detail", "")
            suggestion = iss.get("suggestion", "")
            snippet = iss.get("snippet", "")

            lines.append("### %s [%s] %s" % (sev_icon, sev_label, issue_type))
            lines.append("")
            lines.append("- **位置**: 第 %s 行" % line_num)
            lines.append("- **问题**: %s" % detail)
            if suggestion:
                lines.append("- **建议**: %s" % suggestion)
            if snippet:
                lines.append("")
                lines.append("```java")
                lines.append(snippet[:200])
                lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")

    final_report = "\n".join(lines)

    final_payload = {
        "status": "SUCCESS",
        "output": final_report,
        "resultSummary": result_summary,
        "durationMs": duration_ms,
        "totalSteps": 2
    }
    api_post("/task/" + str(task_id) + "/status", final_payload)
    trace(task_id, 2, "TASK_FINISH", "SUCCESS",
          duration_ms=duration_ms,
          extra={"total_steps": 2, "score": score, "high": high_count, "medium": med_count, "low": low_count})
    print("  [Static] task #" + str(task_id) + " SUCCESS (" + str(duration_ms) + "ms) score=" + str(score))


def process_task(task):
    task_id = task["id"]
    input_type = task.get("taskInputType") or "snippet"
    code = task.get("inputContent") or task.get("input") or ""
    task["input"] = code
    task["taskInputType"] = input_type
    print("============================================================", flush=True)
    print("[WORKER] task #" + str(task_id) + ", type=" + str(task.get("taskType")) + ", inputType=" + input_type + ", codeLen=" + str(len(code)), flush=True)
    print("============================================================", flush=True)
    if llm is not None:
        process_task_react(task)
    else:
        process_task_static(task)


def poll_loop():
    mode = "ReAct(LLM)" if llm is not None else "Static"
    print("[WORKER] DevGuard Agent Worker start | mode: " + mode)
    print("[WORKER] Backend: " + BACKEND_BASE + ", poll: " + str(POLL_INTERVAL) + "s")
    print("[WORKER] Worker ID: " + WORKER_ID)
    print("[WORKER] LLM retries: " + str(LLM_MAX_RETRIES))
    print("[WORKER] Msg compress threshold: " + str(MAX_MESSAGES_BEFORE_COMPRESS))
    if redis_client:
        print("[WORKER] Redis lock ENABLED")
    else:
        print("[WORKER] Redis lock DISABLED")

    recover_running_tasks()

    while True:
        try:
            resp = api_get("/task/pending")
            if resp and resp.get("code") == 200:
                for task in resp.get("data", []):
                    tid = task["id"]
                    if try_acquire_lock(tid):
                        start_heartbeat(tid)
                        try:
                            process_task(task)
                        finally:
                            stop_heartbeat()
                            release_lock(tid)
                        break
                else:
                    time.sleep(POLL_INTERVAL)
            else:
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            print("[WORKER] poll error: " + str(e))
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()