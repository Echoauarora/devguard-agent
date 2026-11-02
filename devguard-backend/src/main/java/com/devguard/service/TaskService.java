package com.devguard.service;

import com.devguard.mapper.AgentTaskMapper;
import com.devguard.mapper.AgentSubTaskMapper;
import com.devguard.entity.AgentTask;
import com.devguard.entity.AgentSubTask;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import java.util.Set;
import java.util.HashSet;

@Service

public class TaskService {

//private static final Set<String> VALID_SUBTASK_STATUSES = new HashSet<>(Set.of("PENDING", "RUNNING", "SUCCESS", "FAILED"));
//private static final Set<String> FINAL_SUBTASK_STATUSES = new HashSet<>(Set.of("SUCCESS", "FAILED"));

    // 合法状态枚举
    private static final Set<String> VALID_SUBTASK_STATUSES = new java.util.HashSet<>(java.util.Set.of("PENDING", "RUNNING", "SUCCESS", "FAILED"));
    private static final Set<String> FINAL_SUBTASK_STATUSES = new java.util.HashSet<>(java.util.Set.of("SUCCESS", "FAILED"));
    private static final Set<String> VALID_TASK_STATUSES = new java.util.HashSet<>(java.util.Set.of("PENDING", "RUNNING", "SUCCESS", "FAILED"));
    private static final Set<String> FINAL_TASK_STATUSES = new java.util.HashSet<>(java.util.Set.of("SUCCESS", "FAILED"));




	@Autowired
	private AgentTaskMapper taskMapper;
	@Autowired
	private AgentSubTaskMapper subTaskMapper;

//创建诊断任务
//目的是为了保证事务：主任务和子任务要么同时创建成功，不然就事务回滚

@Transactional(rollbackFor = Exception.class)
public Long createTask(AgentTask task){
	//先填充主任务的默认值
	task.setStatus("PENDING");
	if(task.getTaskType() == null){
		task.setTaskType("code_diagnose");
	}
	if(task.getMaxSteps() == null){
		task.setMaxSteps(6);
	}
	task.setCreatedAt(LocalDateTime.now());
	task.setUpdatedAt(LocalDateTime.now());
	if(task.getPriority() == null){
		task.setPriority(1);
}
	if(task.getTimeoutSeconds() == null){
	task.setTimeoutSeconds(600);
}

	//插入主任务，数据库自增主键自动填回
	taskMapper.insert(task);
	Long taskId = task.getId();
	//根据任务类型生成对应的执行步骤（子任务）
	List<AgentSubTask> subTaskList = initDefaultSubTasks(taskId,task.getTaskType());
	if(!subTaskList.isEmpty()){
	subTaskMapper.batchInsert(subTaskList);
}
	return taskId;
}

//根据任务的ID进行查询任务详情
public AgentTask getTaskById(Long id){

	return taskMapper.selectById(id);
}



//更新任务的状态，自动记录开始/结束，封装状态运转的逻辑

// 更新任务的状态，自动记录开始/结束时间，支持传入总耗时
public int updateTaskStatus(Long taskId, String status, Long durationMs,String resultSummary) {

// 1. 基础参数校验
        if (taskId == null) {
            throw new IllegalArgumentException("任务ID不能为空");
        }
        if (!VALID_TASK_STATUSES.contains(status)) {
            throw new IllegalArgumentException("非法的任务状态: " + status);
        }

        // 2. 状态流转合法性校验
        AgentTask oldTask = taskMapper.selectById(taskId);
        if (oldTask == null) {
            throw new IllegalArgumentException("任务不存在: " + taskId);
        }

        // 终态不可变更原则
        if (FINAL_TASK_STATUSES.contains(oldTask.getStatus())) {
            // 幂等兼容：相同状态重复调用直接返回
            if (oldTask.getStatus().equals(status)) {
                return 0;
            }
            throw new IllegalStateException("终态任务不可修改状态，当前状态: " + oldTask.getStatus());
        }


    AgentTask task = new AgentTask();
    task.setId(taskId);
    task.setStatus(status);
    task.setDurationMs(durationMs);
    task.setResultSummary(resultSummary);

    // 状态流转时自动记录对应的时间节点
    if ("RUNNING".equals(status)) {
        task.setStartedAt(java.time.LocalDateTime.now());
    } else if ("SUCCESS".equals(status) || ("FAILED".equals(status))) {
        task.setFinishedAt(java.time.LocalDateTime.now());
    }

    return taskMapper.updateById(task);
}

// 重载方法：兼容只传状态的旧调用
public int updateTaskStatus(Long taskId, String status) {  

  return updateTaskStatus(taskId, status, null);
}

public int updateTaskStatus(Long taskId,String status,Long durationMs){

	return updateTaskStatus(taskId,status,durationMs,null);
}

//获取待执行的任务，按照优先级降序，创建时间升序

public List<AgentTask> listPendingTasks(){

	return taskMapper.selectPendingTasks();
}



//初始化默认子任务列表，根据任务类型生成不同的执行步骤

public List<AgentSubTask> initDefaultSubTasks(Long taskId,String taskType){

	List<AgentSubTask> subTaskList = new ArrayList();
	int step = 1;
	LocalDateTime now = LocalDateTime.now();
//第一步，先代码解析
	AgentSubTask parseStep = new AgentSubTask();
	parseStep.setTaskId(taskId);
	parseStep.setStepOrder(step++);
	parseStep.setSubTaskName("代码解析");
	parseStep.setSubTaskType("code_parse");
	parseStep.setStatus("PENDING");
	parseStep.setCreatedAt(now);
	parseStep.setUpdatedAt(now);
	subTaskList.add(parseStep);
//漏洞扫描。缺陷修复类任务，增加漏洞扫描步骤

	if("code_scan".equals(taskType) || "bug_fix".equals(taskType)){
	AgentSubTask scanStep = new AgentSubTask();
	scanStep.setTaskId(taskId);
	scanStep.setStepOrder(step++);
	scanStep.setSubTaskName("漏洞扫描");
	scanStep.setSubTaskType("scan");
	scanStep.setStatus("PENDING");
	scanStep.setCreatedAt(now);
	scanStep.setUpdatedAt(now);
	subTaskList.add(scanStep);
}
//最后一步结果生成
	AgentSubTask generateStep = new AgentSubTask();
	generateStep.setTaskId(taskId);
	generateStep.setStepOrder(step);
	generateStep.setSubTaskName("结果生成");
	generateStep.setSubTaskType("generate");
	generateStep.setStatus("PENDING");
	generateStep.setCreatedAt(now);
	generateStep.setUpdatedAt(now);
	subTaskList.add(generateStep);

	return subTaskList;
}

/**
     * 查询指定任务的所有子任务，按步骤序号排序
     */
    public List<AgentSubTask> listSubTasksByTaskId(Long taskId) {
        return subTaskMapper.selectByTaskId(taskId);
    }

    /**
     * 更新子任务状态与执行结果
     */
    public void updateSubTask(AgentSubTask subTask) {
        //subTask.setUpdatedAt(LocalDateTime.now());
        //return subTaskMapper.updateById(subTask);
	 //参数校验
	if(subTask.getId()==null){
	throw new IllegalArgumentException("子任务id不能为空");

}
	if(subTask.getStatus()!=null && !VALID_SUBTASK_STATUSES.contains(subTask.getStatus())){

	throw new IllegalArgumentException("非法的子任务状态："+subTask.getStatus());
}
	if(subTask.getRetryCount()!=null && subTask.getRetryCount()<0){

	throw new IllegalArgumentException("重试次数不能为负数");
}
	//状态流转合法性检验

	AgentSubTask oldTask = subTaskMapper.selectById(subTask.getId());
	if (oldTask == null){
	throw new IllegalArgumentException("子任务不存在："+subTask.getId());
}
//最终的状态不可变
	if(FINAL_SUBTASK_STATUSES.contains(oldTask.getStatus())){
		if(oldTask.getStatus().equals(subTask.getStatus())){
			return;
}
	throw new IllegalStateException("终态的子任务不可修改状态，当前的状态："+ oldTask.getStatus());
}
//subTaskMapper.updateById(subTask);
// 3. 合法则执行更新
subTaskMapper.updateById(subTask);
}

    public void updateArchiveFields(Long taskId, String inputType, String sandboxPath, String fileTreeJson) {
        AgentTask t2 = new AgentTask();
        t2.setId(taskId);
        t2.setTaskInputType(inputType);
        t2.setSandboxPath(sandboxPath);
        t2.setProjectFileTree(fileTreeJson);
        taskMapper.updateById(t2);
    }



    public List<AgentTask> listAllTasks() {
        return taskMapper.selectAll();
    }


    public void cancelTask(Long taskId, String operator) {
        AgentTask oldTask = taskMapper.selectById(taskId);
        if (oldTask == null) throw new RuntimeException("任务不存在: " + taskId);
        if (FINAL_TASK_STATUSES.contains(oldTask.getStatus())) {
            throw new RuntimeException("终态任务不可取消: " + oldTask.getStatus());
        }
        AgentTask update = new AgentTask();
        update.setId(taskId);
        update.setStatus("CANCELED");
        update.setFinishedAt(java.time.LocalDateTime.now());
        taskMapper.updateById(update);
    }


    public int updateTaskStatus(Long taskId, String status, Long durationMs, String resultSummary,
                                 String output, String errorMsg, String errorCode, Integer totalSteps) {
        AgentTask oldTask = taskMapper.selectById(taskId);
        if (oldTask == null) return 0;
        if (FINAL_TASK_STATUSES.contains(oldTask.getStatus()) && !FINAL_TASK_STATUSES.contains(status)) {
            return 0;
        }
        AgentTask update = new AgentTask();
        update.setId(taskId);
        update.setStatus(status);
        update.setDurationMs(durationMs);
        update.setResultSummary(resultSummary);
        update.setOutput(output);
        update.setErrorMsg(errorMsg);
        update.setTotalSteps(totalSteps);
        if ("RUNNING".equals(status)) update.setStartedAt(java.time.LocalDateTime.now());
        if (FINAL_TASK_STATUSES.contains(status)) update.setFinishedAt(java.time.LocalDateTime.now());
        return taskMapper.updateById(update);
    }

}