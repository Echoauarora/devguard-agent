package com.devguard.controller;

import com.devguard.util.TaskMetrics;
import com.devguard.util.CircuitBreaker;
import com.devguard.util.RedisRateLimiter;
import com.devguard.util.R;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/actuator")
public class HealthController {

    @Autowired(required = false)
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired
    private TaskMetrics taskMetrics;

    @Autowired
    private CircuitBreaker circuitBreaker;

    @Autowired(required = false)
    private RedisRateLimiter rateLimiter;

    @GetMapping("/health")
    public R<Map<String, Object>> health() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");

        Map<String, Object> checks = new HashMap<>();

        try {
            stringRedisTemplate.execute(RedisConnection::ping);
            checks.put("redis", "UP");
        } catch (Exception e) {
            checks.put("redis", "DOWN: " + e.getMessage());
            health.put("status", "DEGRADED");
        }

        try {
            if (jdbcTemplate != null) {
                jdbcTemplate.queryForObject("SELECT 1", Integer.class);
                checks.put("mysql", "UP");
            } else {
                checks.put("mysql", "UNKNOWN");
            }
        } catch (Exception e) {
            checks.put("mysql", "DOWN: " + e.getMessage());
            health.put("status", "DEGRADED");
        }

        // Group 12: 暴露降级状态
        if (rateLimiter != null && !rateLimiter.isRedisAvailable()) {
            checks.put("rate_limiter", "DEGRADED(local-memory)");
        } else {
            checks.put("rate_limiter", rateLimiter != null ? "UP(redis)" : "UNKNOWN");
        }
        health.put("checks", checks);
        return R.ok(health);
    }

    @GetMapping("/metrics")
    public R<Map<String, Object>> metrics() {
        Map<String, Object> all = new HashMap<>();
        all.put("tasks", taskMetrics.snapshot());

        Map<String, Object> circuit = new HashMap<>();
        circuit.put("redis_lock", circuitBreaker.getState("redis_lock").name());
        circuit.put("llm_api", circuitBreaker.getState("llm_api").name());
        all.put("circuitBreakers", circuit);

        all.put("threadInfo", Map.of(
            "totalThreads", Thread.activeCount(),
            "peakMemoryMB", (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1024 / 1024
        ));

        return R.ok(all);
    }
}