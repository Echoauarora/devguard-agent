package com.devguard.common;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.NoHandlerFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 404 路径不存在异常
     */
    @ExceptionHandler(NoHandlerFoundException.class)
    public Result<?> handleNoFoundException(NoHandlerFoundException e) {
        return Result.fail(404, "请求路径不存在");
    }

    /**
     * 参数校验异常
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<?> handleParamException(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldError() != null
                ? e.getBindingResult().getFieldError().getDefaultMessage()
                : "请求参数错误";
        return Result.fail(400, msg);
    }

    /**
     * 数据库约束异常
     */
    @ExceptionHandler(DataIntegrityViolationException.class)
    public Result<?> handleDataException(DataIntegrityViolationException e) {
        return Result.fail(400, "数据操作异常：字段约束不满足");
    }

    /**
     * 业务参数异常
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public Result<?> handleIllegalException(IllegalArgumentException e) {
        return Result.fail(400, e.getMessage());
    }

    /**
     * 兜底所有未捕获的系统异常
     */
    @ExceptionHandler(Exception.class)
    public Result<?> handleException(Exception e) {
        e.printStackTrace();
        return Result.error("系统内部错误，请稍后重试");
    }
}
