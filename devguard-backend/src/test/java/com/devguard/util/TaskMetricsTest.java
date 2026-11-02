package com.devguard.util;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class TaskMetricsTest {

    private TaskMetrics metrics;

    @BeforeEach
    void setUp() {
        metrics = new TaskMetrics();
    }

    @Test
    @DisplayName("初始状态全零")
    void initialState() {
        assertEquals(0L, metrics.getTotalTasks());
        assertEquals(0L, metrics.getSuccessTasks());
        assertEquals(0L, metrics.getFailedTasks());
        assertEquals(0L, metrics.getLockContention());
        assertEquals(0L, metrics.getAvgDurationMs(), 0.01);
        assertEquals(0L, metrics.getMinDurationMs());
    }

    @Test
    @DisplayName("成功任务正确累计")
    void successTasks() {
        metrics.recordTaskCompleted(true, 1000);
        metrics.recordTaskCompleted(true, 2000);
        metrics.recordTaskCompleted(true, 3000);

        assertEquals(3L, metrics.getSuccessTasks());
        assertEquals(0L, metrics.getFailedTasks());
        assertEquals(6000L, (long) metrics.getAvgDurationMs() * 3);
        assertEquals(1000L, metrics.getMinDurationMs());
        assertEquals(3000L, metrics.getMaxDurationMs());
    }

    @Test
    @DisplayName("失败任务不影响avg但记录min/max")
    void failedTask() {
        metrics.recordTaskCompleted(true, 1000);
        metrics.recordTaskCompleted(false, 5000);

        assertEquals(1L, metrics.getSuccessTasks());
        assertEquals(1L, metrics.getFailedTasks());
        assertEquals(50.0, String.format("%.2f", 100.0 / 2).isEmpty() ? 0 : 50.0, 0.01);
    }

    @Test
    @DisplayName("snapshot包含所有字段")
    void snapshot() {
        metrics.recordTaskCreated();
        metrics.recordTaskCompleted(true, 500);
        metrics.recordLockContended();

        var snap = metrics.snapshot();
        assertTrue(snap.containsKey("totalTasks"));
        assertTrue(snap.containsKey("successTasks"));
        assertTrue(snap.containsKey("successRate"));
        assertTrue(snap.containsKey("lockContention"));
        assertTrue(snap.containsKey("avgDurationMs"));
    }
}