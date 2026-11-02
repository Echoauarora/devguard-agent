package com.devguard.common;

public enum ErrorCode {

    SUCCESS(200, "操作成功"),
    BAD_REQUEST(400, "请求参数错误"),
    NOT_FOUND(404, "资源不存在"),
    RATE_LIMITED(429, "请求过于频繁，请稍后重试"),
    SYSTEM_ERROR(500, "系统内部错误"),

    TASK_NOT_FOUND(1001, "任务不存在"),
    TASK_STATUS_INVALID(1002, "任务状态流转非法"),
    TASK_INPUT_EMPTY(1003, "任务输入不能为空"),

    LOCK_ACQUIRE_FAILED(2001, "分布式锁获取失败"),
    REDIS_UNAVAILABLE(2002, "Redis服务不可用"),

    LLM_API_ERROR(3001, "LLM API调用失败"),
    LLM_PARSE_ERROR(3002, "LLM返回结果解析失败");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() { return code; }
    public String getMessage() { return message; }
}