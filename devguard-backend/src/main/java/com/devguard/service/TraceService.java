package com.devguard.service;

import com.devguard.entity.AgentTraceLog;
import com.devguard.mapper.AgentTraceLogMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TraceService {

    @Autowired
    private AgentTraceLogMapper traceMapper;

    public AgentTraceLog addTrace(Long taskId, Integer stepNum, String eventType, String eventDetail, Long durationMs, String extra) {
        AgentTraceLog trace = new AgentTraceLog();
        trace.setTaskId(taskId);
        trace.setStepNum(stepNum);
        trace.setEventType(eventType);
        trace.setEventDetail(eventDetail);
        trace.setDurationMs(durationMs);
        trace.setExtra(extra);
        traceMapper.insert(trace);
        return trace;
    }

    public List<AgentTraceLog> getTracesByTaskId(Long taskId) {
        return traceMapper.selectByTaskId(taskId);
    }

    public List<AgentTraceLog> getTracesByTaskIdAndStepNum(Long taskId, Integer stepNum) {
        return traceMapper.selectByTaskIdAndStepNum(taskId, stepNum);
    }
}