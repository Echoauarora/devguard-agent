package com.devguard.common;

import lombok.Data;

@Data
public class Result<T>{

//状态码，200成功，400是参数或者业务错误，500是系统错误

private int code;

//提示信息

private String message;

//返回数值

private T data;

//成功返回带数值

public static <T> Result<T> success(T data){
Result<T> result = new Result<>();
result.setCode(200);
result.setMessage("success");
result.setData(data);
return result;
}

//业务失败返回

public static <T> Result<T> fail(int code,String message){
Result<T> result = new Result<>();
result.setCode(code);
result.setMessage(message);
return result;
}

//系统错误返回

public static <T> Result<T> error(String message){
Result<T> result = new Result<>();
result.setCode(500);
result.setMessage(message);
return result;
}
}
