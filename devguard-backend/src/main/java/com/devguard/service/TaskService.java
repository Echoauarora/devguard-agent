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

@Service

public class TaskService {

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
public int updateTaskStatus(Long taskId, String status, Long durationMs) {
    AgentTask task = new AgentTask();
    task.setId(taskId);
    task.setStatus(status);
    task.setDurationMs(durationMs);

    // 状态流转时自动记录对应的时间节点
    if ("RUNNING".equals(status)) {
        task.setStartedAt(LocalDateTime.now());
    } else if ("SUCCESS".equals(status) || ("FAILED".equals(status))) {
        task.setFinishedAt(LocalDateTime.now());
    }

    return taskMapper.updateById(task);
}

// 重载方法：兼容只传状态的旧调用
public int updateTaskStatus(Long taskId, String status) {
    return updateTaskStatus(taskId, status, null);
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
    public int updateSubTask(AgentSubTask subTask) {
        subTask.setUpdatedAt(LocalDateTime.now());
        return subTaskMapper.updateById(subTask);
    }

}

