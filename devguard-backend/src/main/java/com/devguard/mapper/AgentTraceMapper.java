package com.devguard.mapper;

import com.devguard.entity.AgentTrace;
import java.util.List;

public interface AgentTraceMapper{

int insert(AgentTrace trace);

List<AgentTrace>selectByTaskId(Long taskId);

List<AgentTrace>selectBySubTaskId(Long subTaskId);
}
