package com.devguard.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AgentSubTask{

	private Long id;
	private Long taskId;
	private Integer stepOrder;
	private String subTaskName;
	private String subTaskType;
	private String status;
	private String inputContent;
	private String outputContent;
	private String errorMsg;
	private Integer retryCount;
	private LocalDateTime startedAt;
	private LocalDateTime finishedAt;
	private Long durationMs;
	private LocalDateTime createdAt;
	private LocalDateTime updatedAt;
}

