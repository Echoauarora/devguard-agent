package com.devguard;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.devguard.mapper")
public class DevGuardApplication {
	public static void main(String[] args){
		SpringApplication.run(DevGuardApplication.class,args);
		}
	}

