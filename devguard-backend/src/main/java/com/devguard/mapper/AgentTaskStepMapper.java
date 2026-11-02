package com.devguard.mapper;

import com.devguard.entity.AgentTaskStep;
import java.util.List;

public interface AgentTaskStepMapper {

    int insert(AgentTaskStep step);

    AgentTaskStep selectById(Long id);

    List<AgentTaskStep> selectByTaskId(Long taskId);

    List<AgentTaskStep> selectSuccessByTaskId(Long taskId);

    int updateById(AgentTaskStep step);

}
