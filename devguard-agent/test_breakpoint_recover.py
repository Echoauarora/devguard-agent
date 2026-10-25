import os
# ========== 数据库配置 ==========
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "root"
os.environ["DB_PASSWORD"] = "7299018"  
os.environ["DB_NAME"] = "devguard"

# ========== 大模型配置 ==========
os.environ["LLM_API_KEY"] = "sk-62b76670831b419eb7ad26626eb1c491"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL"] = "deepseek-flash"

from agent.persistent_planner_agent import PersistentPlannerAgent

if __name__ == "__main__":
    print("[断点恢复] 开始扫描中断任务...")
    
    # 调用恢复方法：自动扫描所有 RUNNING 状态的任务，从断点继续执行
    PersistentPlannerAgent.recover_running_tasks()
    
    print("[断点恢复] 所有中断任务处理完成")
