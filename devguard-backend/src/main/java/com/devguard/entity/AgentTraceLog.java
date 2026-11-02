package com.devguard.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AgentTraceLog {
    private Long id;
    private Long taskId;
    // Group 11: 快照版本号 - 恢复执行时校验兼容性
    private Integer version;
    private Integer stepNum;
    private String eventType;
    private String eventDetail;
    private Long durationMs;
    private LocalDateTime timestamp;
    private String extra;
}