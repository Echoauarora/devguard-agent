package com.devguard.util;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class RedisRateLimiter {

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    private static final String RATE_LIMIT_PREFIX = "devguard:rate_limit:";

    // Group 12: Redis 降级 - 本地内存滑动窗口（单机模式）
    private final ConcurrentHashMap<String, AtomicLong> localCounter = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AtomicLong> localWindowStart = new ConcurrentHashMap<>();
    private volatile boolean redisAvailable = true;
    private static final int REDIS_FAIL_THRESHOLD = 3;
    private final AtomicLong redisFailCount = new AtomicLong(0);

    private static final String SLIDING_WINDOW_LUA =
            "local key = KEYS[1]\n" +
            "local window_ms = tonumber(ARGV[1])\n" +
            "local max_count = tonumber(ARGV[2])\n" +
            "local now = tonumber(ARGV[3])\n" +
            "local window_start = now - window_ms\n" +
            "redis.call('ZREMRANGEBYSCORE', key, 0, window_start)\n" +
            "local current_count = redis.call('ZCARD', key)\n" +
            "if current_count >= max_count then\n" +
            "    return 0\n" +
            "end\n" +
            "redis.call('ZADD', key, now, now)\n" +
            "redis.call('EXPIRE', key, math.ceil(window_ms / 1000) + 1)\n" +
            "return 1";

    private final DefaultRedisScript<Long> limitScript;

    public RedisRateLimiter() {
        limitScript = new DefaultRedisScript<>();
        limitScript.setScriptText(SLIDING_WINDOW_LUA);
        limitScript.setResultType(Long.class);
    }

    public boolean tryAcquire(String key, int windowSeconds, int maxCount) {
        String redisKey = RATE_LIMIT_PREFIX + key;
        long windowMs = windowSeconds * 1000L;
        long now = System.currentTimeMillis();

        // Group 12: 降级开关 - Redis DOWN 超过3次后切本地
        if (!redisAvailable) {
            return localTryAcquire(key, windowSeconds, maxCount, now);
        }

        try {
            Long result = stringRedisTemplate.execute(
                    limitScript,
                    Collections.singletonList(redisKey),
                    String.valueOf(windowMs),
                    String.valueOf(maxCount),
                    String.valueOf(now)
            );
            redisFailCount.set(0);
            return result != null && result == 1;
        } catch (Exception e) {
            long fails = redisFailCount.incrementAndGet();
            System.err.println("[RateLimiter] Redis fail count=" + fails);
            if (fails >= REDIS_FAIL_THRESHOLD) {
                redisAvailable = false;
                System.err.println("[RateLimiter] REDIS DEGRADED → local-memory mode");
            }
            return localTryAcquire(key, windowSeconds, maxCount, now);
        }
    }

    // Group 12: 本地内存限流降级（单机滑动窗口）
    private boolean localTryAcquire(String key, int windowSeconds, int maxCount, long now) {
        AtomicLong counter = localCounter.computeIfAbsent(key, k -> new AtomicLong(0));
        AtomicLong windowStart = localWindowStart.computeIfAbsent(key, k -> new AtomicLong(now));
        if (now - windowStart.get() > windowSeconds * 1000L) {
            counter.set(0);
            windowStart.set(now);
        }
        long current = counter.incrementAndGet();
        if (current > maxCount) {
            counter.decrementAndGet();
            return false;
        }
        return true;
    }

    public void resetDegraded() {
        this.redisAvailable = true;
        this.redisFailCount.set(0);
    }

    public boolean isRedisAvailable() {
        return redisAvailable;
    }
}