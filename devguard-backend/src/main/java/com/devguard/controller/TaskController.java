package com.devguard.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.devguard.entity.AgentTask;
import com.devguard.service.TaskService;
import com.devguard.entity.AgentSubTask;
import com.devguard.common.Result;
import java.util.List;
import java.time.LocalDateTime;

//用来接受请求，转发参数，结果返回，不包含业务逻辑
@RestController
@RequestMapping("/task")
public class TaskController{

@Autowired
private TaskService taskService;


//创建诊断任务，目的是生成任务id；

@PostMapping
public Result<Long> createTask(@RequestBody AgentTask task){
//	return taskService.createTask(task);

	Long taskId = taskService.createTask(task);
	return Result.success(taskId);
}


//根据任务的id查询任务的详情


@GetMapping("/{id}")
public Result<AgentTask> getTaskById(@PathVariable Long id){

	//return taskService.getTaskById(id);
	AgentTask task = taskService.getTaskById(id);
	if(task == null){
	return Result.fail(404,"任务不存在");
}
	return Result.success(task);
}

//查询任务中等待执行的任务列表，把等待返回的任务列表进行返回

@GetMapping("/pending")
public Result<List<AgentTask>> listPendingTasks(){

//	return taskService.listPendingTasks();
	List<AgentTask> tasks = taskService.listPendingTasks();
	return Result.success(tasks);
}

//更新任务的状态，包含id，目标状态，影响的 行数
//更新任务的状态，包含id，目标状态，总耗时；开始/结束时间由后端自动生成
@PutMapping("/{id}/status")
public Result<Void> updateStatus(@PathVariable Long id,
                                  @RequestParam String status,
                                  @RequestParam(required = false) Long durationMs) {
    taskService.updateTaskStatus(id, status, durationMs);
    return Result.success(null);
}


@GetMapping("/{id}/subtasks")
    public Result<List<AgentSubTask>> listSubTasks(@PathVariable Long id) {
        //return taskService.listSubTasksByTaskId(id);
	//先校验任务存不存在

	AgentTask task = taskService.getTaskById(id);
	if(task == null){

	return Result.fail(404,"任务不存在");
}
List<AgentSubTask> subTasks = taskService.listSubTasksByTaskId(id);
	return Result.success(subTasks);
}

   // 更新子任务状态与执行结果
    @PutMapping("/subtask/{id}")
    public Result<Void> updateSubTask(@PathVariable Long id, @RequestBody AgentSubTask subTask) {
        subTask.setId(id);
        //return taskService.updateSubTask(subTask);
	 //int row = taskService.updateSubTask(subTask);
	//return Result.success(row);

	taskService.updateSubTask(subTask);
	return Result.success(null);
}
}
