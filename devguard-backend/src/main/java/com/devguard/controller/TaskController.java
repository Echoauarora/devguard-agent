package com.devguard.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.devguard.entity.AgentTask;
import com.devguard.entity.AgentSubTask;
import com.devguard.entity.AgentTaskStep;
import com.devguard.entity.AgentTraceLog;
import com.devguard.service.TaskService;
import com.devguard.common.Result;
import com.devguard.mapper.AgentTaskStepMapper;
import com.devguard.mapper.AgentTraceLogMapper;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.multipart.MultipartFile;
import com.devguard.service.ArchiveService;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/task")
public class TaskController {

    @Autowired
    private TaskService taskService;

    @Autowired
    private AgentTaskStepMapper stepMapper;

    @Autowired
    private AgentTraceLogMapper traceLogMapper;

    @Autowired(required = false)
    private RedisTemplate<String, String> redisTemplate;

    @Autowired
    private ArchiveService archiveService;

    @PostMapping
    public Result<?> createTask(@RequestBody AgentTask task,
                                 @RequestHeader(value = "X-Request-Id", required = false) String requestId) {
        // Group 15: 幂等 - 相同 requestId 30分钟内直接返回已存在的 taskId
        if (requestId != null && !requestId.isEmpty()) {
            String dedupKey = "task:dedup:" + requestId;
            try {
                Boolean exists = redisTemplate.hasKey(dedupKey);
                if (Boolean.TRUE.equals(exists)) {
                    Object cached = redisTemplate.opsForValue().get(dedupKey);
                    if (cached != null) {
                        Map<String, Object> r = new java.util.HashMap<>();
                        r.put("taskId", Long.valueOf(cached.toString()));
                        r.put("idempotent", true);
                        return Result.success(r);
                    }
                }
            } catch (Exception ignored) {}
        }
        // Group 10: 输入脏数据校验
        if (task.getInputContent() != null && task.getInputContent().length() > 50000) {
            return Result.fail(400, "代码输入超过50KB限制");
        }
        if (task.getInputContent() != null && task.getInputContent().indexOf('\u0000') >= 0) {
            return Result.fail(400, "输入包含非法字符");
        }
        Long taskId = taskService.createTask(task);
        // Group 15b: 缓存 taskId 供幂等查询
        if (requestId != null && !requestId.isEmpty()) {
            try {
                redisTemplate.opsForValue().set("task:dedup:" + requestId, taskId.toString(),
                    30, java.util.concurrent.TimeUnit.MINUTES);
            } catch (Exception ignored) {}
        }
        Map<String, Object> r = new java.util.HashMap<>();
        r.put("taskId", taskId);
        return Result.success(r);
    }

    @GetMapping("/{id}")
    public Result<AgentTask> getTaskById(@PathVariable Long id) {
        AgentTask task = taskService.getTaskById(id);
        if (task == null) return Result.fail(404, "任务不存在");
        return Result.success(task);
    }

    @GetMapping("/pending")
    public Result<List<AgentTask>> listPendingTasks() {
        return Result.success(taskService.listPendingTasks());
    }

    @GetMapping("/running")
    public Result<List<AgentTask>> listRunningTasks() {
        List<AgentTask> all = taskService.listAllTasks();
        java.util.List<AgentTask> running = new java.util.ArrayList<>();
        if (all != null) {
            for (AgentTask t : all) {
                if ("RUNNING".equals(t.getStatus())) running.add(t);
            }
        }
        return Result.success(running);
    }

    @GetMapping("/all")
    public Result<List<AgentTask>> listAllTasks() {
        return Result.success(taskService.listAllTasks());
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id,
                                     @RequestParam String status,
                                     @RequestParam(required = false) Long durationMs,
                                     @RequestParam(required = false) String resultSummary) {
        taskService.updateTaskStatus(id, status, durationMs, resultSummary, null, null, null, null);
        return Result.success(null);
    }

    @PostMapping("/{id}/status")
    public Result<Void> updateStatusPost(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        String status = (String) body.get("status");
        Long durationMs = body.get("durationMs") != null ? Long.valueOf(body.get("durationMs").toString()) : null;
        String resultSummary = (String) body.get("resultSummary");
        String output = (String) body.get("output");
        String errorMsg = (String) body.get("errorMsg");
        String errorCode = (String) body.get("errorCode");
        Integer totalSteps = body.get("totalSteps") != null ? Integer.valueOf(body.get("totalSteps").toString()) : null;
        taskService.updateTaskStatus(id, status, durationMs, resultSummary, output, errorMsg, errorCode, totalSteps);
        return Result.success(null);
    }

    @GetMapping("/{id}/subtasks")
    public Result<List<AgentSubTask>> listSubTasks(@PathVariable Long id) {
        AgentTask task = taskService.getTaskById(id);
        if (task == null) return Result.fail(404, "任务不存在");
        return Result.success(taskService.listSubTasksByTaskId(id));
    }

    @GetMapping("/{id}/steps")
    public Result<List<AgentTaskStep>> listSteps(@PathVariable Long id) {
        return Result.success(stepMapper.selectByTaskId(id));
    }

    @PostMapping("/{id}/step")
    public Result<Map<String, Object>> addStep(@PathVariable Long id, @RequestBody AgentTaskStep step) {
        step.setTaskId(id);
        stepMapper.insert(step);
        Map<String, Object> r = new java.util.HashMap<>();
        r.put("id", step.getId());
        return Result.success(r);
    }

    @PostMapping("/step/{stepId}")
    public Result<Void> updateStep(@PathVariable Long stepId, @RequestBody AgentTaskStep step) {
        step.setId(stepId);
        stepMapper.updateById(step);
        return Result.success(null);
    }

    @PutMapping("/subtask/{id}")
    public Result<Void> updateSubTask(@PathVariable Long id, @RequestBody AgentSubTask subTask) {
        subTask.setId(id);
        taskService.updateSubTask(subTask);
        return Result.success(null);
    }

    @PostMapping("/{id}/cancel")
    public Result<Void> cancelTask(@PathVariable Long id, @RequestParam(defaultValue = "user") String operator) {
        taskService.cancelTask(id, operator);
        return Result.success(null);
    }
    @PostMapping("/upload-zip")
    public Result<Map<String, Object>> uploadZip(@RequestParam("file") MultipartFile file,
                                                  @RequestParam(defaultValue = "code_diagnose") String taskType,
                                                  @RequestParam(defaultValue = "10") Integer maxSteps) {
        if (file.isEmpty()) return Result.fail(400, "文件为空");
        String origName = file.getOriginalFilename() == null ? "" : file.getOriginalFilename();
        if (!origName.toLowerCase().endsWith(".zip")) return Result.fail(400, "只支持 .zip 文件");
        if (file.getSize() > 50 * 1024 * 1024) return Result.fail(400, "超过50MB");

        AgentTask task = new AgentTask();
        task.setTaskName(origName);
        task.setTaskType(taskType);
        task.setTaskInputType("zip_project");
        task.setStatus("PARSING_ARCHIVE");
        task.setInputContent(origName);
        task.setMaxSteps(maxSteps);
        Long taskId = taskService.createTask(task);

        try {
            ArchiveService.SandboxResult sr = archiveService.processZip(file, taskId);
            taskService.updateArchiveFields(taskId, "zip_project", sr.sandboxPath, sr.fileTreeJson);
            AgentTask upd = new AgentTask();
            upd.setId(taskId);
            upd.setStatus("PENDING");
            taskService.updateTaskStatus(taskId, "PENDING", null, null, null, null, null, null);

            Map<String, Object> r = new java.util.HashMap<>();
            r.put("taskId", taskId);
            r.put("fileCount", sr.fileList.size());
            r.put("totalBytes", sr.totalBytes);
            r.put("sandboxPath", sr.sandboxPath);
            return Result.success(r);
        } catch (ArchiveService.ArchiveException e) {
            AgentTask upd = new AgentTask();
            upd.setId(taskId);
            upd.setStatus("FAILED");
            upd.setErrorMsg(e.getMessage());
            taskService.updateTaskStatus(taskId, "FAILED", null, null, null, e.getMessage(), null, null);
            return Result.fail(400, "归档解析失败: " + e.getMessage());
        }
    }

    @GetMapping("/project/read-file")
    public Result<Map<String, Object>> readProjectFile(@RequestParam Long taskId,
                                                       @RequestParam String filePath,
                                                       @RequestParam(defaultValue = "30000") int maxChars) {
        try {
            String content = archiveService.readFile(taskId, filePath, maxChars);
            Map<String, Object> r = new java.util.HashMap<>();
            r.put("content", content);
            r.put("truncated", content.length() >= maxChars);
            return Result.success(r);
        } catch (ArchiveService.ArchiveException e) {
            return Result.fail(404, e.getMessage());
        }
    }

    @GetMapping("/project/list-files")
    public Result<List<String>> listProjectFiles(@RequestParam Long taskId) {
        try {
            return Result.success(archiveService.listFiles(taskId));
        } catch (ArchiveService.ArchiveException e) {
            return Result.fail(404, e.getMessage());
        }
    }

}
