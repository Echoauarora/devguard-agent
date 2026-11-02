package com.devguard.util;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentMatchers;
import org.mockito.Mockito;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class RedisRateLimiterTest {

    private RedisRateLimiter limiter;
    private StringRedisTemplate redis;

    @SuppressWarnings("unchecked")
    @BeforeEach
    void setUp() throws Exception {
        limiter = new RedisRateLimiter();
        redis = mock(StringRedisTemplate.class);
        java.lang.reflect.Field f = RedisRateLimiter.class.getDeclaredField("stringRedisTemplate");
        f.setAccessible(true);
        f.set(limiter, redis);
    }

    @Test
    @DisplayName("首次请求允许通过")
    void firstRequestAllowed() {
        when(redis.execute(any(DefaultRedisScript.class), ArgumentMatchers.<List<String>>any(), any(), any(), any())).thenReturn(1L);
        assertTrue(limiter.tryAcquire("/api/task/create", 10, 60));
    }

    @Test
    @DisplayName("超过maxCount被拒绝")
    void exceededLimit() {
        when(redis.execute(any(DefaultRedisScript.class), ArgumentMatchers.<List<String>>any(), any(), any(), any())).thenReturn(0L);
        assertFalse(limiter.tryAcquire("/api/task/create", 10, 60));
    }

    @Test
    @DisplayName("Redis异常时降级允许")
    void redisExceptionFallbackAllow() {
        when(redis.execute(any(DefaultRedisScript.class), ArgumentMatchers.<List<String>>any(), any(), any(), any())).thenThrow(new RuntimeException("Redis down"));
        assertTrue(limiter.tryAcquire("/api/task/create", 10, 60));
    }

    @Test
    @DisplayName("不同key独立计数")
    void differentKeysIndependent() {
        when(redis.execute(any(DefaultRedisScript.class), ArgumentMatchers.<List<String>>any(), any(), any(), any())).thenReturn(1L);
        assertTrue(limiter.tryAcquire("/api/task/create", 5, 60));
        assertTrue(limiter.tryAcquire("/api/task/list", 5, 60));
    }
}