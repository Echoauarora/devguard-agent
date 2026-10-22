// package com.devguard.util;

// import org.springframework.data.redis.core.StringRedisTemplate;
// import org.springframework.stereotype.Component;

// import javax.annotation.Resource;
// import java.util.concurrent.TimeUnit;

// /**
//  * Redis 分布式限流工具
//  * 固定窗口计数器算法，原子操作保证并发安全
//  */
// @Component
// public class RedisRateLimiter {

//     @Resource
//     private StringRedisTemplate stringRedisTemplate;

//     private static final String RATE_LIMIT_PREFIX = "devguard:rate_limit:";

//     /**
//      * 尝试获取限流令牌
//      * @param key 限流唯一标识（如 ip:path）
//      * @param windowSeconds 时间窗口，单位秒
//      * @param maxCount 窗口内最大请求数
//      * @return 是否允许通过
//      */
//     public boolean tryAcquire(String key, int windowSeconds, int maxCount) {
//         String redisKey = RATE_LIMIT_PREFIX + key;

//         // 原子递增
//         Long count = stringRedisTemplate.opsForValue().increment(redisKey);

//         // 第一次访问，设置过期时间
//         if (count != null && count == 1) {
//             stringRedisTemplate.expire(redisKey, windowSeconds, TimeUnit.SECONDS);
//         }

//         // 判断是否超过阈值
//         return count != null && count <= maxCount;
//     }
// }
package com.devguard.util;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Collections;

/**
 * Redis 分布式限流工具
 * 滑动窗口计数器算法，Lua脚本保证原子操作
 * 解决固定窗口边界突刺问题，限流更精准
 */
@Component
public class RedisRateLimiter {

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    private static final String RATE_LIMIT_PREFIX = "devguard:rate_limit:";

    /**
     * 滑动窗口限流 Lua 脚本
     * 原子执行：移除过期记录 -> 统计当前数量 -> 判断是否超限 -> 插入新记录
     */
       private static final String SLIDING_WINDOW_LUA =
            "local key = KEYS[1]\n" +
            "local window_ms = tonumber(ARGV[1])\n" +
            "local max_count = tonumber(ARGV[2])\n" +
            "local now = tonumber(ARGV[3])\n" +
            "local window_start = now - window_ms\n" +
            "-- 移除窗口外的旧记录\n" +
            "redis.call('ZREMRANGEBYSCORE', key, 0, window_start)\n" +
            "-- 统计当前窗口内的请求数\n" +
            "local current_count = redis.call('ZCARD', key)\n" +
            "-- 超过阈值，直接拒绝\n" +
            "if current_count >= max_count then\n" +
            "    return 0\n" +
            "end\n" +
            "-- 没超限，插入当前请求的时间戳\n" +
            "redis.call('ZADD', key, now, now)\n" +
            "-- 设置过期时间，比窗口稍长一点，避免冷key残留\n" +
            "redis.call('EXPIRE', key, math.ceil(window_ms / 1000) + 1)\n" +
            "return 1";

    private final DefaultRedisScript<Long> limitScript;

    public RedisRateLimiter() {
        limitScript = new DefaultRedisScript<>();
        limitScript.setScriptText(SLIDING_WINDOW_LUA);
        limitScript.setResultType(Long.class);
    }

    /**
     * 尝试获取限流令牌
     * @param key 限流唯一标识（如 ip:path）
     * @param windowSeconds 时间窗口，单位秒
     * @param maxCount 窗口内最大请求数
     * @return 是否允许通过
     */
    // public boolean tryAcquire(String key, int windowSeconds, int maxCount) {
    //     String redisKey = RATE_LIMIT_PREFIX + key;
    //     long windowMs = windowSeconds * 1000L;
    //     long now = System.currentTimeMillis();

    //     Long result = stringRedisTemplate.execute(
    //             limitScript,
    //             Collections.singletonList(redisKey),
    //             String.valueOf(windowMs),
    //             String.valueOf(maxCount),
    //             String.valueOf(now)
    //     );

    //     return result != null && result == 1;
    // }
    public boolean tryAcquire(String key, int windowSeconds, int maxCount) {
        String redisKey = RATE_LIMIT_PREFIX + key;
        long windowMs = windowSeconds * 1000L;
        long now = System.currentTimeMillis();

        try {
            Long result = stringRedisTemplate.execute(
                    limitScript,
                    Collections.singletonList(redisKey),
                    String.valueOf(windowMs),
                    String.valueOf(maxCount),
                    String.valueOf(now)
            );
            System.out.println("[滑动窗口限流] key=" + redisKey + "，当前计数结果=" + result);
            return result != null && result == 1;
        } catch (Exception e) {
            System.err.println("[滑动窗口限流] 执行异常：" + e.getMessage());
            e.printStackTrace();
            return true; // 异常时默认放行，避免误拦截
        }
    }

}

