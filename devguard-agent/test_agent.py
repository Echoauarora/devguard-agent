import os
os.environ["LLM_API_KEY"] = "sk-62b76670831b419eb7ad26626eb1c491"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL"] = "deepseek-flash"

# from agent.simple_agent import SimpleAgent
from agent.planner_agent import PlannerAgent

if __name__ =="__main__":
    # agent = SimpleAgent()
    agent = PlannerAgent(max_steps = 5)
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
    user_input = f"帮我全面诊断诊断java代码，先统计代码结构信息，在扫描所有的问题，最后给出完整的修复报告：\n{test_code}"

    print("=====================用户输入====================")
    print(user_input)
    print("\n==========================Agent执行中...=====================")

    result = agent.run(user_input)

    print("\n=================Agent最终诊断报告==========================")

    print(result)