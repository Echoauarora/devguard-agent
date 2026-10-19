package com.devguard.entity;

import lombok.Data;
import java.time.LocalDateTime;
@Data
public class AgentTrace{
 	private Long id;
	private Long taskId;
	private Long subTaskId;
	private String traceType;
	private String content;
	private String toolName;
	private Long costMs;
	private LocalDateTime createdAt;

}
