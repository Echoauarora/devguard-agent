package com.devguard.util;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CircuitBreakerTest {

    private CircuitBreaker cb;
    private StringRedisTemplate redis;
    private ValueOperations<String, String> valueOps;

    @SuppressWarnings("unchecked")
    @BeforeEach
    void setUp() throws Exception {
        cb = new CircuitBreaker();
        redis = mock(StringRedisTemplate.class);
        valueOps = mock(ValueOperations.class);
        java.lang.reflect.Field f = CircuitBreaker.class.getDeclaredField("stringRedisTemplate");
        f.setAccessible(true);
        f.set(cb, redis);
        when(redis.opsForValue()).thenReturn(valueOps);
    }

    @Test
    @DisplayName("初始状态CLOSED")
    void initialClosed() {
        when(valueOps.get("devguard:circuit:test:open")).thenReturn(null);
        when(valueOps.get("devguard:circuit:test:fails")).thenReturn(null);
        assertEquals(CircuitBreaker.State.CLOSED, cb.getState("test"));
    }

    @Test
    @DisplayName("CLOSED状态允许请求")
    void closedAllows() {
        when(valueOps.get("devguard:circuit:test:open")).thenReturn(null);
        when(valueOps.get("devguard:circuit:test:fails")).thenReturn(null);
        assertTrue(cb.allowRequest("test"));
    }

    @Test
    @DisplayName("OPEN状态拒绝请求")
    void openRejects() {
        when(valueOps.get("devguard:circuit:test:open")).thenReturn("1");
        assertFalse(cb.allowRequest("test"));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState("test"));
    }

    @Test
    @DisplayName("连续失败5次触发熔断")
    void fiveFailuresOpensCircuit() {
        when(valueOps.get("devguard:circuit:test:open")).thenReturn(null);
        when(valueOps.increment("devguard:circuit:test:fails")).thenReturn(1L, 2L, 3L, 4L, 5L);

        for (int i = 0; i < 4; i++) {
            cb.recordFailure("test");
        }
        cb.recordFailure("test");

        verify(valueOps).set(eq("devguard:circuit:test:open"), eq("1"), eq(30L), eq(TimeUnit.SECONDS));
    }

    @Test
    @DisplayName("成功后清除失败计数")
    void successClearsFails() {
        cb.recordSuccess("test");
        verify(redis).delete("devguard:circuit:test:fails");
    }
}