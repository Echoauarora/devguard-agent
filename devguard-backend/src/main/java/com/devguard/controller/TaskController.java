package com.devguard.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.devguard.entity.AgentTask;
import com.devguard.service.TaskService;

import java.util.List;


//用来接受请求，转发参数，结果返回，不包含业务逻辑
@RestController
@RequestMapping("/api/task")
public class TaskController{

@Autowired
private TaskService taskService;


//创建诊断任务，目的是生成任务id；

@PostMapping
public Long createTask(@RequestBody AgentTask task){

	return taskService.createTask(task);
}


//根据任务的id查询任务的详情


@GetMapping("/{id}")
public AgentTask getTaskById(@PathVariable Long id){

	return taskService.getTaskById(id);
}

//查询任务中等待执行的任务列表，把等待返回的任务列表进行返回

@GetMapping("/pending")
public List<AgentTask> listPendingTasks(){

	return taskService.listPendingTasks();
}

//更新任务的状态，包含id，目标状态，影响的 行数

@PutMapping("/{id}/status")
public int updateTaskStatus(@PathVariable Long id,@RequestParam String status){

	return taskService.updateTaskStatus(id,status);
}
}
