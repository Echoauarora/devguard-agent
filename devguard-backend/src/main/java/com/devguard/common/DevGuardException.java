package com.devguard.common;

public class DevGuardException extends RuntimeException {

    private final ErrorCode errorCode;

    public DevGuardException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }

    public DevGuardException(ErrorCode errorCode, String detail) {
        super(errorCode.getMessage() + ": " + detail);
        this.errorCode = errorCode;
    }

    public DevGuardException(int code, String message) {
        super(message);
        this.errorCode = null;
        this.code = code;
    }

    private int code;

    public ErrorCode getErrorCode() { return errorCode; }

    public int getCode() { return errorCode != null ? errorCode.getCode() : code; }
}