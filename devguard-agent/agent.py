import time
from api import TaskApi, ms_to_iso
from code_analyzer import JavaCodeAnalyzer

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
