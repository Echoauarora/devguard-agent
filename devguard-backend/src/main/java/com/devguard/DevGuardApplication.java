package com.devguard;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.retry.annotation.EnableRetry;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@org.springframework.scheduling.annotation.EnableScheduling
@org.springframework.retry.annotation.EnableRetry
@MapperScan("com.devguard.mapper")
public class DevGuardApplication {
	public static void main(String[] args){
		SpringApplication.run(DevGuardApplication.class,args);
		}
	}

