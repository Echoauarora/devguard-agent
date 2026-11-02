package com.devguard.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Service
public class ArchiveService {

    private static final long MAX_FILE_SIZE = 50 * 1024 * 1024;
    private static final long MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024;
    private static final long MAX_COMPRESSION_RATIO = 200;

    private static final Set<String> EXCLUDED_DIRS = Set.of(
            ".git", "target", "build", "out", "node_modules", ".idea",
            ".vscode", "__pycache__", ".venv", "venv", "dist"
    );

    private static final Set<String> INCLUDED_EXTS = Set.of(
            ".java", ".go", ".py", ".js", ".ts", ".jsx", ".tsx",
            ".xml", ".yml", ".yaml", ".properties", ".gradle",
            ".pom", ".json", ".html", ".css", ".sql", ".md"
    );

    private static final Set<String> INCLUDED_NAMES = Set.of(
            "pom.xml", "build.gradle", "package.json", "go.mod",
            "requirements.txt", "Dockerfile", "Makefile", ".classpath", ".project"
    );

    private static final String SANDBOX_ROOT = System.getProperty("java.io.tmpdir") + "/devguard-sandbox";

    public SandboxResult processZip(MultipartFile file, Long taskId) throws ArchiveException {
        validateFile(file);

        try {
            Path sandboxDir = Paths.get(SANDBOX_ROOT, String.valueOf(taskId));
            Files.createDirectories(sandboxDir);

            long totalUncompressed = 0;
            List<String> fileTree = new ArrayList<>();
            Map<String, String> entryContentCache = new HashMap<>();

            try (ZipInputStream zis = new ZipInputStream(file.getInputStream())) {
                ZipEntry entry;
                while ((entry = zis.getNextEntry()) != null) {
                    if (entry.isDirectory()) continue;
                    String entryName = sanitizeEntryName(entry.getName());
                    if (entryName == null) continue;

                    Path targetPath = sandboxDir.resolve(entryName).normalize();
                    if (!targetPath.startsWith(sandboxDir)) {
                        throw new ArchiveException("路径穿越攻击: " + entryName);
                    }

                    if (!isIncluded(targetPath.getFileName().toString())) continue;
                    if (isInExcludedDir(targetPath)) continue;

                    Files.createDirectories(targetPath.getParent());
                    try (OutputStream os = Files.newOutputStream(targetPath)) {
                        byte[] buf = new byte[8192];
                        int read;
                        long entrySize = 0;
                        while ((read = zis.read(buf)) > 0) {
                            os.write(buf, 0, read);
                            entrySize += read;
                            totalUncompressed += read;
                            if (totalUncompressed > MAX_UNCOMPRESSED_SIZE) {
                                throw new ArchiveException("解压后超过" + (MAX_UNCOMPRESSED_SIZE / 1024 / 1024) + "MB限制");
                            }
                        }
                        if (entrySize == 0 && !targetPath.toString().toLowerCase().endsWith(".java")) continue;
                    } catch (IOException e) {
                        throw new ArchiveException("解压失败: " + entryName, e);
                    }

                    fileTree.add(entryName);
                }
            }

            if (fileTree.isEmpty()) {
                throw new ArchiveException("压缩包内无可分析的源码文件");
            }

            Collections.sort(fileTree);

            String fileTreeJson;
            try {
                fileTreeJson = new ObjectMapper().writeValueAsString(fileTree);
            } catch (Exception e) {
                fileTreeJson = "[]";
            }
            return new SandboxResult(
                    sandboxDir.toString(),
                    fileTreeJson,
                    fileTree,
                    totalUncompressed
            );

        } catch (ArchiveException e) {
            cleanupSandbox(taskId);
            throw e;
        } catch (IOException e) {
            cleanupSandbox(taskId);
            throw new ArchiveException("解压IO异常", e);
        }
    }

    private void validateFile(MultipartFile file) throws ArchiveException {
        if (file == null || file.isEmpty()) {
            throw new ArchiveException("文件为空");
        }
        String name = file.getOriginalFilename();
        if (name == null || !name.toLowerCase().endsWith(".zip")) {
            throw new ArchiveException("仅支持.zip格式");
        }
        long size = file.getSize();
        if (size > MAX_FILE_SIZE) {
            throw new ArchiveException("文件超过" + (MAX_FILE_SIZE / 1024 / 1024) + "MB限制");
        }
        if (size < 100) {
            throw new ArchiveException("文件太小，疑似损坏");
        }
    }

    private String sanitizeEntryName(String name) throws ArchiveException {
        if (name.contains("..")) {
            throw new ArchiveException("非法路径: " + name);
        }
        String normalized = name.replace('\\', '/');
        while (normalized.startsWith("/")) normalized = normalized.substring(1);
        return normalized.isEmpty() ? null : normalized;
    }

    private boolean isIncluded(String fileName) {
        String lower = fileName.toLowerCase();
        if (INCLUDED_NAMES.contains(lower)) return true;
        return INCLUDED_EXTS.stream().anyMatch(lower::endsWith);
    }

    private boolean isInExcludedDir(Path path) {
        for (Path part : path) {
            if (EXCLUDED_DIRS.contains(part.toString())) return true;
        }
        return false;
    }

    public String readFile(Long taskId, String filePath, int maxChars) throws ArchiveException {
        Path sandboxDir = Paths.get(SANDBOX_ROOT, String.valueOf(taskId));
        Path target = sandboxDir.resolve(filePath).normalize();

        if (!target.startsWith(sandboxDir)) {
            throw new ArchiveException("越权访问: " + filePath);
        }
        if (!Files.exists(target) || !Files.isRegularFile(target)) {
            throw new ArchiveException("文件不存在: " + filePath);
        }

        try {
            String content = Files.readString(target);
            if (maxChars > 0 && content.length() > maxChars) {
                return content.substring(0, maxChars) + "\n... [截断]";
            }
            return content;
        } catch (IOException e) {
            throw new ArchiveException("读取失败: " + filePath, e);
        }
    }

    public List<String> listFiles(Long taskId) throws ArchiveException {
        Path sandboxDir = Paths.get(SANDBOX_ROOT, String.valueOf(taskId));
        if (!Files.exists(sandboxDir)) {
            throw new ArchiveException("沙箱目录不存在，任务可能未完成解压");
        }
        try (Stream<Path> walk = Files.walk(sandboxDir)) {
            return walk.filter(p -> Files.isRegularFile(p))
                    .map(p -> sandboxDir.relativize(p).toString().replace('\\', '/'))
                    .sorted()
                    .collect(Collectors.toList());
        } catch (IOException e) {
            throw new ArchiveException("遍历文件失败", e);
        }
    }

    public void cleanupSandbox(Long taskId) {
        try {
            Path sandboxDir = Paths.get(SANDBOX_ROOT, String.valueOf(taskId));
            if (Files.exists(sandboxDir)) {
                Files.walk(sandboxDir)
                        .sorted((a, b) -> b.getNameCount() - a.getNameCount())
                        .forEach(p -> {
                            try { Files.deleteIfExists(p); } catch (IOException ignored) {}
                        });
            }
        } catch (Exception ignored) {}
    }

    public void cleanupExpired() {
        try {
            Path root = Paths.get(SANDBOX_ROOT);
            if (!Files.exists(root)) return;
            long expireMs = 6L * 60 * 60 * 1000;
            long now = System.currentTimeMillis();
            try (Stream<Path> dirs = Files.list(root)) {
                dirs.filter(Files::isDirectory)
                        .forEach(d -> {
                            try {
                                long mtime = Files.getLastModifiedTime(d).toMillis();
                                if (now - mtime > expireMs) cleanupSandbox(Long.parseLong(d.getFileName().toString()));
                            } catch (Exception ignored) {}
                        });
            }
        } catch (Exception ignored) {}
    }

    public static class SandboxResult {
        public final String sandboxPath;
        public final String fileTreeJson;
        public final List<String> fileList;
        public final long totalBytes;

        public SandboxResult(String sandboxPath, String fileTreeJson, List<String> fileList, long totalBytes) {
            this.sandboxPath = sandboxPath;
            this.fileTreeJson = fileTreeJson;
            this.fileList = fileList;
            this.totalBytes = totalBytes;
        }
    }

    public static class ArchiveException extends Exception {
        public ArchiveException(String msg) { super(msg); }
        public ArchiveException(String msg, Throwable cause) { super(msg, cause); }
    }
}