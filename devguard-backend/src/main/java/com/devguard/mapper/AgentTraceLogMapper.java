package com.devguard.mapper;

import com.devguard.entity.AgentTraceLog;
import java.util.List;

public interface AgentTraceLogMapper {
    int insert(AgentTraceLog trace);
    List<AgentTraceLog> selectByTaskId(Long taskId);
    List<AgentTraceLog> selectByTaskIdAndStepNum(Long taskId, Integer stepNum);
}