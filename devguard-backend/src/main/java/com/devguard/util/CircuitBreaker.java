package com.devguard.util;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class CircuitBreaker {

    public enum State { CLOSED, OPEN, HALF_OPEN }

    private static final String CB_PREFIX = "devguard:circuit:";
    private static final int FAIL_THRESHOLD = 5;
    private static final int RECOVER_SECONDS = 30;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    public boolean allowRequest(String resource) {
        String openKey = CB_PREFIX + resource + ":open";
        String failKey = CB_PREFIX + resource + ":fails";

        String openFlag = stringRedisTemplate.opsForValue().get(openKey);
        if ("1".equals(openFlag)) {
            return false;
        }

        String failCount = stringRedisTemplate.opsForValue().get(failKey);
        int count = failCount == null ? 0 : Integer.parseInt(failCount);
        if (count >= FAIL_THRESHOLD) {
            stringRedisTemplate.opsForValue().set(openKey, "1", RECOVER_SECONDS, TimeUnit.SECONDS);
            stringRedisTemplate.delete(failKey);
            return false;
        }
        return true;
    }

    public void recordSuccess(String resource) {
        String failKey = CB_PREFIX + resource + ":fails";
        stringRedisTemplate.delete(failKey);
    }

    public void recordFailure(String resource) {
        String failKey = CB_PREFIX + resource + ":fails";
        String openKey = CB_PREFIX + resource + ":open";
        Long newCount = stringRedisTemplate.opsForValue().increment(failKey);
        if (newCount != null && newCount == 1) {
            stringRedisTemplate.expire(failKey, 60, TimeUnit.SECONDS);
        }
        if (newCount != null && newCount >= FAIL_THRESHOLD) {
            stringRedisTemplate.opsForValue().set(openKey, "1", RECOVER_SECONDS, TimeUnit.SECONDS);
            stringRedisTemplate.delete(failKey);
        }
    }

    public State getState(String resource) {
        String openFlag = stringRedisTemplate.opsForValue().get(CB_PREFIX + resource + ":open");
        if ("1".equals(openFlag)) {
            return State.OPEN;
        }
        String failCount = stringRedisTemplate.opsForValue().get(CB_PREFIX + resource + ":fails");
        int count = failCount == null ? 0 : Integer.parseInt(failCount);
        if (count > 0 && count < FAIL_THRESHOLD) {
            return State.HALF_OPEN;
        }
        return State.CLOSED;
    }
}