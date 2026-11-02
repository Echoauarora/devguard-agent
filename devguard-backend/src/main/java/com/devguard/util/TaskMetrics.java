package com.devguard.util;

import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

@Component
public class TaskMetrics {

    private final LongAdder totalTasks = new LongAdder();
    private final LongAdder successTasks = new LongAdder();
    private final LongAdder failedTasks = new LongAdder();
    private final LongAdder lockContention = new LongAdder();
    private final AtomicLong totalDurationMs = new AtomicLong(0);
    private final AtomicLong maxDurationMs = new AtomicLong(0);
    private final AtomicLong minDurationMs = new AtomicLong(Long.MAX_VALUE);

    public void recordTaskCreated() { totalTasks.increment(); }

    public void recordTaskCompleted(boolean success, long durationMs) {
        if (success) successTasks.increment();
        else failedTasks.increment();
        totalDurationMs.addAndGet(durationMs);
        maxDurationMs.updateAndGet(cur -> Math.max(cur, durationMs));
        minDurationMs.updateAndGet(cur -> Math.min(cur, durationMs));
    }

    public void recordLockContended() { lockContention.increment(); }

    public long getTotalTasks() { return totalTasks.sum(); }
    public long getSuccessTasks() { return successTasks.sum(); }
    public long getFailedTasks() { return failedTasks.sum(); }
    public long getLockContention() { return lockContention.sum(); }
    public long getMaxDurationMs() { return maxDurationMs.get(); }
    public long getMinDurationMs() {
        long v = minDurationMs.get();
        return v == Long.MAX_VALUE ? 0 : v;
    }
    public double getAvgDurationMs() {
        long success = successTasks.sum();
        return success == 0 ? 0 : (double) totalDurationMs.get() / success;
    }

    public Map<String, Object> snapshot() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("totalTasks", getTotalTasks());
        m.put("successTasks", getSuccessTasks());
        m.put("failedTasks", getFailedTasks());
        m.put("successRate", getTotalTasks() == 0 ? 0 : String.format("%.2f%%", 100.0 * getSuccessTasks() / getTotalTasks()));
        m.put("lockContention", getLockContention());
        m.put("avgDurationMs", String.format("%.0f", getAvgDurationMs()));
        m.put("maxDurationMs", getMaxDurationMs());
        m.put("minDurationMs", getMinDurationMs());
        return m;
    }
}