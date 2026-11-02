package com.devguard.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AgentTaskStep {

    private Long id;
    private Long taskId;
    private Integer stepNum;
    private String stepType;
    private String toolName;
    private String inputSnapshot;
    private String outputSnapshot;
    private String status;
    private String errorMsg;
    private Long durationMs;
    private LocalDateTime createdAt;
    private LocalDateTime finishedAt;

}
