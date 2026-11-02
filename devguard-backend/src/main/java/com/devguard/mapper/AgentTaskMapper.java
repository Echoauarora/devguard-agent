package com.devguard.mapper;

import com.devguard.entity.AgentTask;
import java.util.List;

public interface AgentTaskMapper{
	int insert(AgentTask task);

	AgentTask selectById(Long id);

	int updateById(AgentTask task);

	List<AgentTask> selectPendingTasks();

        List<AgentTask> selectAll();
}
