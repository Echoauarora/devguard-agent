import re
from typing import List, Dict, Tuple


class JavaCodeAnalyzer:
    """Java 代码基础静态分析器"""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.total_lines = len(self.lines)

    def count_effective_lines(self) -> int:
        """统计有效代码行数：去除空行、单行注释"""
        count = 0
        in_block_comment = False
        for line in self.lines:
            stripped = line.strip()
            # 块注释处理
            if '/*' in stripped:
                in_block_comment = True
            if '*/' in stripped:
                in_block_comment = False
                continue
            if in_block_comment:
                continue
            # 跳过空行和单行注释
            if not stripped or stripped.startswith('//'):
                continue
            count += 1
        return count

    def extract_class_name(self) -> List[str]:
        """提取所有类名"""
        class_pattern = re.compile(r'(?:public\s+)?(?:class|interface)\s+(\w+)')
        return class_pattern.findall(self.code)

    def extract_methods(self) -> List[Dict[str, str]]:
        """提取方法名和参数列表"""
        method_pattern = re.compile(
            r'(?:public|private|protected|static|final|abstract|synchronized)\s+'
            r'[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)'
        )
        methods = []
        for match in method_pattern.finditer(self.code):
            method_name = match.group(1)
            params = match.group(2).strip()
            methods.append({
                "name": method_name,
                "params": params if params else "无参数"
            })
        return methods

    def check_simple_issues(self) -> List[str]:
        """简易代码问题检测：空catch块、硬编码密码、打印语句"""
        issues = []
        # 空 catch 块
        empty_catch = re.compile(r'catch\s*\([^)]+\)\s*\{\s*\}')
        if empty_catch.search(self.code):
            issues.append("存在空 catch 块，异常被吞，建议补充异常处理逻辑")

        # 硬编码密码
        password_pattern = re.compile(r'(password|passwd|pwd)\s*=\s*["\']\w+["\']', re.IGNORECASE)
        if password_pattern.search(self.code):
            issues.append("存在硬编码密码字符串，建议配置化存储")

        # 控制台打印语句（生产环境不建议）
        if 'System.out.println' in self.code:
            issues.append("使用了 System.out.println 控制台打印，生产环境建议使用日志框架")

        # 括号匹配检查
        if self.code.count('{') != self.code.count('}'):
            issues.append("大括号数量不匹配，可能存在语法错误")

        return issues

    def analyze(self) -> Dict:
        """执行完整分析，返回结构化结果"""
        classes = self.extract_class_name()
        methods = self.extract_methods()
        issues = self.check_simple_issues()
        effective_lines = self.count_effective_lines()

        return {
            "total_lines": self.total_lines,
            "effective_lines": effective_lines,
            "class_count": len(classes),
            "class_names": classes,
            "method_count": len(methods),
            "methods": methods,
            "issues": issues
        }
