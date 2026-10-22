package com.devguard.interceptor;

import com.devguard.util.RedisRateLimiter;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.HashMap;
import java.util.Map;

/**
 * 全局限流拦截器
 */
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    @Resource
    private RedisRateLimiter rateLimiter;

    private final ObjectMapper objectMapper = new ObjectMapper();

    // 不同接口的限流配置：路径 -> [窗口秒数, 最大请求数]
    private static final Map<String, int[]> LIMIT_CONFIG = new HashMap<>();

    static {
        // 任务提交接口：严格限流，每分钟最多10次
        LIMIT_CONFIG.put("/api/task", new int[]{60, 10});
        // 任务查询接口：宽松限流，每分钟最多60次
        LIMIT_CONFIG.put("/api/task/", new int[]{60, 60});
    }

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {

System.out.println("[限流拦截器] 收到请求：" + request.getRequestURI());

        String ip = getClientIp(request);
        String path = request.getRequestURI();

        // 匹配限流规则
        int[] config = matchLimitConfig(path);
        if (config == null) {
            // 没有配置的接口直接放行
            return true;
        }

        int windowSeconds = config[0];
        int maxCount = config[1];
        String limitKey = ip + ":" + path;

        boolean allowed = rateLimiter.tryAcquire(limitKey, windowSeconds, maxCount);

        if (!allowed) {
            // 触发限流，返回 429
            response.setStatus(429);
            response.setContentType("application/json;charset=UTF-8");

            Map<String, Object> result = new HashMap<>();
            result.put("code", 429);
            result.put("message", "请求过于频繁，请稍后再试");
            result.put("data", null);

            response.getWriter().write(objectMapper.writeValueAsString(result));
            return false;
        }

        return true;
    }

    /**
     * 匹配限流规则，前缀匹配
     */
    private int[] matchLimitConfig(String path) {
        for (Map.Entry<String, int[]> entry : LIMIT_CONFIG.entrySet()) {
            if (path.startsWith(entry.getKey())) {
                return entry.getValue();
            }
        }
        return null;
    }

    /**
     * 获取客户端真实IP
     */
    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        // 多个代理的情况，第一个IP为客户端真实IP
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}
