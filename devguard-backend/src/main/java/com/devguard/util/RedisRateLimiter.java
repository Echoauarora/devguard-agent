package com.devguard.util;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.concurrent.TimeUnit;

/**
 * Redis 分布式限流工具
 * 固定窗口计数器算法，原子操作保证并发安全
 */
@Component
public class RedisRateLimiter {

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    private static final String RATE_LIMIT_PREFIX = "devguard:rate_limit:";

    /**
     * 尝试获取限流令牌
     * @param key 限流唯一标识（如 ip:path）
     * @param windowSeconds 时间窗口，单位秒
     * @param maxCount 窗口内最大请求数
     * @return 是否允许通过
     */
    public boolean tryAcquire(String key, int windowSeconds, int maxCount) {
        String redisKey = RATE_LIMIT_PREFIX + key;

        // 原子递增
        Long count = stringRedisTemplate.opsForValue().increment(redisKey);

        // 第一次访问，设置过期时间
        if (count != null && count == 1) {
            stringRedisTemplate.expire(redisKey, windowSeconds, TimeUnit.SECONDS);
        }

        // 判断是否超过阈值
        return count != null && count <= maxCount;
    }
}
