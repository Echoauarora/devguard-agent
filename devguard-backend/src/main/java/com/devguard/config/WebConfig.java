package com.devguard.config;

import com.devguard.interceptor.RateLimitInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import javax.annotation.Resource;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    // 构造方法：类被实例化时就会打印
    public WebConfig() {
        System.out.println("===== WebConfig 配置类已被Spring加载 =====");
    }

    @Resource
    private RateLimitInterceptor rateLimitInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        System.out.println("===== 开始注册限流拦截器 =====");
        registry.addInterceptor(rateLimitInterceptor)
                .addPathPatterns("/**");
    }
}
