package com.devguard.controller;

import com.devguard.entity.AgentTraceLog;
import com.devguard.service.TraceService;
import com.devguard.util.R;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/trace")
public class TraceController {

    @Autowired
    private TraceService traceService;

    @PostMapping("/log")
    public R<AgentTraceLog> logTrace(@RequestBody Map<String, Object> body) {
        Long taskId = body.get("taskId") != null ? Long.valueOf(body.get("taskId").toString()) : null;
        Integer stepNum = body.get("stepNum") != null ? Integer.valueOf(body.get("stepNum").toString()) : null;
        String eventType = (String) body.get("eventType");
        String eventDetail = (String) body.get("eventDetail");
        Long durationMs = body.get("durationMs") != null ? Long.valueOf(body.get("durationMs").toString()) : null;
        String extra = (String) body.get("extra");
        if (taskId == null || eventType == null) return R.fail("taskId和eventType不能为空");
        AgentTraceLog saved = traceService.addTrace(taskId, stepNum, eventType, eventDetail, durationMs, extra);
        return R.ok(saved);
    }

    @GetMapping("/task/{taskId}")
    public R<List<AgentTraceLog>> getByTask(@PathVariable Long taskId) {
        return R.ok(traceService.getTracesByTaskId(taskId));
    }

    @GetMapping("/task/{taskId}/step/{stepNum}")
    public R<List<AgentTraceLog>> getByTaskStep(@PathVariable Long taskId, @PathVariable Integer stepNum) {
        return R.ok(traceService.getTracesByTaskIdAndStepNum(taskId, stepNum));
    }
}