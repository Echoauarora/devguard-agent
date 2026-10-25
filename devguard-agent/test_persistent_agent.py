import os
# 数据库配置（根据你的环境修改）
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "root"
os.environ["DB_PASSWORD"] = "7299018"
os.environ["DB_NAME"] = "devguard"

# 大模型配置
os.environ["LLM_API_KEY"] = "sk-62b76670831b419eb7ad26626eb1c491"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL"] = "deepseek-flash"

from agent.persistent_planner_agent import PersistentPlannerAgent

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

    agent = PersistentPlannerAgent(max_steps=5)
    result = agent.run_new_task(user_input)

    print("\n===================== 最终诊断报告 =====================")
    print(result)
