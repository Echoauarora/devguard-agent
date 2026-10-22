import time
import concurrent.futures
from api import TaskApi, ms_to_iso
from code_analyzer import JavaCodeAnalyzer
from redis_lock import RedisDistributedLock


class TimeoutError(Exception):
    """子任务执行超时异常"""
    pass


class TaskExecutor:
    def __init__(self):
        self.api = TaskApi()
        self.poll_interval = 3
        self.max_retry = 3        # 单个子任务最大重试次数
        self.subtask_timeout = 30  # 单个子任务超时阈值，单位秒
        self.lock = RedisDistributedLock()  # 分布式任务锁

    def run(self):
        print("Agent 启动成功，开始轮询任务...")
        while True:
            try:
                pending_tasks = self.api.get_pending_tasks()
                if not pending_tasks:
                    time.sleep(self.poll_interval)
                    continue

                # 遍历待办任务，尝试抢锁
                task = None
                for t in pending_tasks:
                    task_id = t["id"]
                    if self.lock.try_lock(task_id):
                        task = t
                        break

                if not task:
                    # 所有任务都被其他 Agent 锁定，等待下一轮
                    time.sleep(self.poll_interval)
                    continue

                task_id = task["id"]
                task_type = task["taskType"]
                print(f"\n抢到任务: ID={task_id}, 类型={task_type}")

                # 拿到锁后再更新状态
                lock_success = self.api.update_task_status(task_id, "RUNNING")
                if not lock_success:
                    print(f"任务 {task_id} 锁定失败，可能被其他 Agent 抢走了")
                    self.lock.unlock(task_id)
                    time.sleep(self.poll_interval)
                    continue

                self._execute_task(task)

            except Exception as e:
                print(f"轮询异常: {e}")
                time.sleep(self.poll_interval)

    def _run_with_timeout(self, func, *args, timeout=None):
        """带超时控制执行函数，超时抛出 TimeoutError"""
        if timeout is None:
            timeout = self.subtask_timeout

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise TimeoutError(f"执行超时，超过 {timeout} 秒")

    def _is_retryable_error(self, e: Exception) -> bool:
        """判断异常是否可重试：网络/超时类可重试；业务逻辑/语法错误不可重试"""
        if isinstance(e, TimeoutError):
            return True
        error_msg = str(e).lower()
        retryable_keywords = ["timeout", "connection", "network", "500", "502", "503"]
        return any(keyword in error_msg for keyword in retryable_keywords)

    def _build_result_summary(self, sub_tasks_output) -> str:
        """
        汇总子任务结果，生成主任务摘要
        :param sub_tasks_output: 子任务结果列表 [(sub_type, output)]
        """
        total_issues = 0
        top_issues = []

        for sub_type, output in sub_tasks_output:
            if sub_type == "scan":
                lines = output.strip().split("\n")
                for line in lines:
                    if line.startswith("问题") and "：" in line:
                        total_issues += 1
                        if len(top_issues) < 2:
                            issue_desc = line.split("：", 1)[1].strip()
                            top_issues.append(issue_desc)

        if total_issues == 0:
            return "扫描完成，未检测到基础代码问题"

        summary = f"扫描完成，共检测到 {total_issues} 个问题"
        if top_issues:
            summary += "：" + "、".join(top_issues)
            if total_issues > 2:
                summary += f" 等{total_issues}项"
        return summary

    def _execute_task(self, task):
        task_id = task["id"]
        # 记录主任务本地开始时间，用于计算总耗时
        task_start_ms = int(time.time() * 1000)

        try:
            sub_tasks = self.api.get_sub_tasks(task_id)
            if not sub_tasks:
                print(f"任务 {task_id} 没有子任务，直接完成")
                self.api.update_task_status(task_id, "SUCCESS")
                self.lock.unlock(task_id)
                return

            sub_tasks.sort(key=lambda x: x["stepOrder"])
            sub_outputs = []  # 收集子任务输出，用于汇总摘要

            for sub_task in sub_tasks:
                sub_id = sub_task["id"]
                sub_name = sub_task["subTaskName"]
                sub_type = sub_task["subTaskType"]
                retry_count = 0
                success = False
                last_error = None

                print(f"  执行子任务: {sub_name} ({sub_type})")

                while retry_count <= self.max_retry:
                    try:
                        # 子任务开始：记录时间并回写
                        sub_start_ms = int(time.time() * 1000)
                        sub_start_iso = ms_to_iso(sub_start_ms)
                        self.api.update_sub_task(sub_id, "RUNNING",
                                                started_at=sub_start_iso,
                                                retry_count=retry_count)

                        # 带超时执行业务逻辑
                        output = self._run_with_timeout(
                            self._run_sub_task, sub_type, task.get("inputContent", "")
                        )

                        # 子任务成功结束
                        sub_end_ms = int(time.time() * 1000)
                        sub_end_iso = ms_to_iso(sub_end_ms)
                        duration_ms = sub_end_ms - sub_start_ms

                        self.api.update_sub_task(sub_id, "SUCCESS",
                                                output_content=output,
                                                finished_at=sub_end_iso,
                                                duration_ms=duration_ms,
                                                retry_count=retry_count)

                        sub_outputs.append((sub_type, output))  # 收集输出用于汇总
                        print(f"  子任务完成: {sub_name}，耗时 {duration_ms}ms，重试 {retry_count} 次")
                        success = True
                        break

                    except Exception as e:
                        last_error = str(e)
                        retry_count += 1
                        print(f"  子任务 {sub_name} 失败(第{retry_count}次): {e}")

                        # 判断是否可重试
                        if not self._is_retryable_error(e) or retry_count > self.max_retry:
                            # 最终失败，记录错误信息
                            sub_end_ms = int(time.time() * 1000)
                            sub_end_iso = ms_to_iso(sub_end_ms)
                            duration_ms = sub_end_ms - sub_start_ms
                            self.api.update_sub_task(sub_id, "FAILED",
                                                    error_msg=last_error,
                                                    finished_at=sub_end_iso,
                                                    duration_ms=duration_ms,
                                                    retry_count=retry_count - 1)
                            print(f"  子任务 {sub_name} 最终失败，累计重试 {retry_count-1} 次")
                            break

                        # 重试间隔 1 秒，避免打爆接口
                        time.sleep(1)

                if not success:
                    # 单个子任务失败，整个任务标记失败
                    task_end_ms = int(time.time() * 1000)
                    total_duration = task_end_ms - task_start_ms
                    fail_summary = f"执行失败：子任务[{sub_name}]异常，{last_error}"

                    print(f"任务 {task_id} 因子任务失败终止")
                    self.api.update_task_status(task_id, "FAILED",
                                               duration_ms=total_duration,
                                               result_summary=fail_summary)
                    self.lock.unlock(task_id)
                    return

            # 主任务成功结束：汇总结果并回填
            task_end_ms = int(time.time() * 1000)
            total_duration = task_end_ms - task_start_ms
            result_summary = self._build_result_summary(sub_outputs)

            self.api.update_task_status(task_id, "SUCCESS",
                                       duration_ms=total_duration,
                                       result_summary=result_summary)
            print(f"任务 {task_id} 全部执行完成，总耗时 {total_duration}ms")
            self.lock.unlock(task_id)

        except Exception as e:
            # 任务异常：记录耗时并释放锁
            task_end_ms = int(time.time() * 1000)
            total_duration = task_end_ms - task_start_ms
            print(f"任务 {task_id} 执行异常: {e}")
            self.api.update_task_status(task_id, "FAILED", duration_ms=total_duration)
            self.lock.unlock(task_id)

    def _run_sub_task(self, sub_type: str, code: str) -> str:
        """根据子任务类型执行对应逻辑，返回结果字符串"""

        if sub_type == "code_parse":
            # 代码解析阶段：真实静态分析
            analyzer = JavaCodeAnalyzer(code)
            result = analyzer.analyze()

            output = "=== 代码解析结果 ===\n"
            output += f"总行数：{result['total_lines']}\n"
            output += f"有效代码行数：{result['effective_lines']}\n"
            output += f"类数量：{result['class_count']}\n"
            output += f"类名：{', '.join(result['class_names'])}\n"
            output += f"方法数量：{result['method_count']}\n"
            for idx, method in enumerate(result['methods'], 1):
                output += f"  方法{idx}：{method['name']}({method['params']})\n"
            return output

        elif sub_type == "scan":
            # 漏洞扫描阶段：基于分析结果做问题检测
            analyzer = JavaCodeAnalyzer(code)
            issues = analyzer.check_simple_issues()

            output = "=== 漏洞扫描结果 ===\n"
            if not issues:
                output += "未检测到基础代码问题\n"
            else:
                for idx, issue in enumerate(issues, 1):
                    output += f"问题{idx}：{issue}\n"
            return output

        elif sub_type == "generate":
            # 结果生成阶段：汇总信息
            analyzer = JavaCodeAnalyzer(code)
            result = analyzer.analyze()
            issues = result['issues']

            output = "=== 扫描任务总结 ===\n"
            output += f"代码规模：{result['effective_lines']} 行有效代码\n"
            output += f"包含 {result['class_count']} 个类，{result['method_count']} 个方法\n"
            output += f"检测到 {len(issues)} 个基础问题\n"
            if issues:
                output += "主要问题：" + "；".join(issues[:2]) + "\n"
            output += "扫描完成"
            return output

        else:
            return f"未知子任务类型：{sub_type}"


if __name__ == "__main__":
    executor = TaskExecutor()
    executor.run()
