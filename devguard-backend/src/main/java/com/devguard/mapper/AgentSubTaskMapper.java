package com.devguard.mapper;

import com.devguard.entity.AgentSubTask;
import java.util.List;

public interface AgentSubTaskMapper{

	int batchInsert(List<AgentSubTask> subTaskList);

	List<AgentSubTask> selectByTaskId(Long taskId);

	int updateById(AgentSubTask subTask);

}
