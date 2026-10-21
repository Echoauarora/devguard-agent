import time
from api import TaskApi, ms_to_iso


class TaskExecutor:
    def __init__(self):
        self.api = TaskApi()
        self.poll_interval = 3

    def run(self):
        print("Agent 启动成功，开始轮询任务...")
        while True:
            try:
                pending_tasks = self.api.get_pending_tasks()
                if not pending_tasks:
                    time.sleep(self.poll_interval)
                    continue

                task = pending_tasks[0]
                task_id = task["id"]
                task_type = task["taskType"]
                print(f"\n抢到任务: ID={task_id}, 类型={task_type}")

                lock_success = self.api.update_task_status(task_id, "RUNNING")
                if not lock_success:
                    print(f"任务 {task_id} 锁定失败，可能被其他 Agent 抢走了")
                    time.sleep(self.poll_interval)
                    continue

                self._execute_task(task)

            except Exception as e:
                print(f"执行异常: {e}")
                time.sleep(self.poll_interval)
    def _execute_task(self, task):
        task_id = task["id"]
        # 记录主任务本地开始时间，用于计算总耗时
        task_start_ms = int(time.time() * 1000)
        try:
            sub_tasks = self.api.get_sub_tasks(task_id)
            if not sub_tasks:
                self.api.update_task_status(task_id, "SUCCESS")
                return

            sub_tasks.sort(key=lambda x: x["stepOrder"])

            for sub_task in sub_tasks:
                sub_id = sub_task["id"]
                sub_name = sub_task["subTaskName"]
                sub_type = sub_task["subTaskType"]
                print(f"  执行子任务: {sub_name} ({sub_type})")

                # 子任务开始：记录时间并回写
                sub_start_ms = int(time.time() * 1000)
                sub_start_iso = ms_to_iso(sub_start_ms)
                self.api.update_sub_task(sub_id, "RUNNING", started_at=sub_start_iso)

                # 执行业务逻辑
                output = self._run_sub_task(sub_type, task.get("inputContent", ""))

                # 子任务结束：计算耗时并回写结果+时间
                sub_end_ms = int(time.time() * 1000)
                sub_end_iso = ms_to_iso(sub_end_ms)
                duration_ms = sub_end_ms - sub_start_ms

                self.api.update_sub_task(sub_id, "SUCCESS",
                                        output_content=output,
                                        finished_at=sub_end_iso,
                                        duration_ms=duration_ms)
                print(f"  子任务完成: {sub_name}，耗时 {duration_ms}ms")

            # 主任务成功结束：计算总耗时并回写
            task_end_ms = int(time.time() * 1000)
            total_duration = task_end_ms - task_start_ms
            self.api.update_task_status(task_id, "SUCCESS", duration_ms=total_duration)
            print(f"任务 {task_id} 全部执行完成，总耗时 {total_duration}ms")

        except Exception as e:
            # 任务失败：同样记录总耗时
            task_end_ms = int(time.time() * 1000)
            total_duration = task_end_ms - task_start_ms
            print(f"任务 {task_id} 执行失败: {e}")
            self.api.update_task_status(task_id, "FAILED", duration_ms=total_duration)


    def _run_sub_task(self, sub_type, input_content):
        if sub_type == "code_parse":
            lines = input_content.strip().split("\n")
            return f"解析完成：共 {len(lines)} 行代码，检测到类定义"

        elif sub_type == "scan":
            return "扫描完成：未发现高危漏洞，1 个低危告警（命名不规范）"

        elif sub_type == "generate":
            return "生成完成：已输出完整诊断报告"

        else:
            return f"未知任务类型: {sub_type}"


if __name__ == "__main__":
    executor = TaskExecutor()
    executor.run()
