package com.devguard.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AgentTask {

        private Long id;
        private String taskName;
        private String taskType;
        private String taskInputType;
        private String sandboxPath;
        private String projectFileTree;
        private String status;
        private Integer priority;
        private Integer timeoutSeconds;
        private String inputContent;
        private String resultSummary;
        private String createdBy;
        private LocalDateTime startedAt;
        private LocalDateTime finishedAt;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private Long durationMs;
        private String input;
        private String output;
        private Integer maxSteps;
        private Integer totalSteps;
        private String errorMsg;

}
