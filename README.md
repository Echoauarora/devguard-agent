#分布式java代码安全审计的Agent系统
基于ReAct模式的异步代码审计智能体，Java + Python + Vue3混合架构，面向Java源码漏洞扫描

#项目简介
-DevGuard 是一个工业级Agent应用，支持Java代码片段提交审计，内置完整任务调度、状态机、断点恢复、限流熔断、全链路追踪能力。
- Java SpringBoot：任务管理、REST接口、状态流转、权限控制
- Python FastAPI Worker：ReAct智能体调度、Function Calling、工具执行
- 中间件：Redis（分布式锁、限流、心跳、消息队列）
- 可观测：SkyWalking Java Agent无侵入采集全链路Trace，配合SSE向前端实时推送Agent步骤日志
> 迭代规划：后续支持Zip工程包上传，实现跨文件源码审计
>
> #技术栈
Java 21 | SpringBoot3 | MyBatis | MySQL8
Python 3.10 | FastAPI | DeepSeek Function Calling
Redis | SkyWalking(Java Agent探针接入) | SSE
Vue3 | Vite
>
> #核心能力
- ReAct 推理循环，工具注册中心 + JSON Schema 参数校验，抑制LLM幻觉
- FSM有限状态机 + 看门狗 + 快照持久化，任务崩溃断点恢复
- 分布式任务锁、接口限流、熔断降级、指数退避重试，覆盖大部分故障场景
- 环路检测、自适应推理步数，避免Agent死循环
- 全链路Trace埋点，日志可追溯
- 基于SkyWalking无侵入采集链路，全链路Trace可追溯，用于排查分布式异步任务异常

- ##快速启动
1. 准备环境变量：DeepSeek API Key、MySQL、Redis配置
2. 启动SpringBoot后端（可挂载SkyWalking Agent探针）
3. 启动Python Agent Worker
4. 启动Vue3前端，提交Java代码，实时查看Agent审计流程
