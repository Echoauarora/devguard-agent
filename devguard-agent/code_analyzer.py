# import re
# from typing import List, Dict, Tuple


# class JavaCodeAnalyzer:
#     """Java 代码基础静态分析器"""

#     def __init__(self, code: str):
#         self.code = code
#         self.lines = code.splitlines()
#         self.total_lines = len(self.lines)

#     def count_effective_lines(self) -> int:
#         """统计有效代码行数：去除空行、单行注释"""
#         count = 0
#         in_block_comment = False
#         for line in self.lines:
#             stripped = line.strip()
#             # 块注释处理
#             if '/*' in stripped:
#                 in_block_comment = True
#             if '*/' in stripped:
#                 in_block_comment = False
#                 continue
#             if in_block_comment:
#                 continue
#             # 跳过空行和单行注释
#             if not stripped or stripped.startswith('//'):
#                 continue
#             count += 1
#         return count

#     def extract_class_name(self) -> List[str]:
#         """提取所有类名"""
#         class_pattern = re.compile(r'(?:public\s+)?(?:class|interface)\s+(\w+)')
#         return class_pattern.findall(self.code)

#     def extract_methods(self) -> List[Dict[str, str]]:
#         """提取方法名和参数列表"""
#         method_pattern = re.compile(
#             r'(?:public|private|protected|static|final|abstract|synchronized)\s+'
#             r'[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)'
#         )
#         methods = []
#         for match in method_pattern.finditer(self.code):
#             method_name = match.group(1)
#             params = match.group(2).strip()
#             methods.append({
#                 "name": method_name,
#                 "params": params if params else "无参数"
#             })
#         return methods

#     def check_simple_issues(self) -> List[str]:
#         """简易代码问题检测：空catch块、硬编码密码、打印语句"""
#         issues = []
#         # 空 catch 块
#         empty_catch = re.compile(r'catch\s*\([^)]+\)\s*\{\s*\}')
#         if empty_catch.search(self.code):
#             issues.append("存在空 catch 块，异常被吞，建议补充异常处理逻辑")

#         # 硬编码密码
#         password_pattern = re.compile(r'(password|passwd|pwd)\s*=\s*["\']\w+["\']', re.IGNORECASE)
#         if password_pattern.search(self.code):
#             issues.append("存在硬编码密码字符串，建议配置化存储")

#         # 控制台打印语句（生产环境不建议）
#         if 'System.out.println' in self.code:
#             issues.append("使用了 System.out.println 控制台打印，生产环境建议使用日志框架")

#         # 括号匹配检查
#         if self.code.count('{') != self.code.count('}'):
#             issues.append("大括号数量不匹配，可能存在语法错误")

#         return issues

#     def analyze(self) -> Dict:
#         """执行完整分析，返回结构化结果"""
#         classes = self.extract_class_name()
#         methods = self.extract_methods()
#         issues = self.check_simple_issues()
#         effective_lines = self.count_effective_lines()

#         return {
#             "total_lines": self.total_lines,
#             "effective_lines": effective_lines,
#             "class_count": len(classes),
#             "class_names": classes,
#             "method_count": len(methods),
#             "methods": methods,
#             "issues": issues
# #         }
# import re


# class JavaCodeAnalyzer:
#     """
#     Java 代码静态分析器
#     支持代码结构解析、规范检查、漏洞检测、性能隐患扫描
#     """

#     def __init__(self, code: str):
#         self.code = code
#         self.lines = code.split("\n")

#     def analyze(self) -> dict:
#         """基础代码结构分析，返回结构化结果"""
#         total_lines = len(self.lines)
#         effective_lines = 0
#         class_count = 0
#         class_names = []
#         method_count = 0
#         methods = []

#         class_pattern = re.compile(r'\bclass\s+(\w+)')
#         method_pattern = re.compile(r'\b(public|private|protected)\s+\w+\s+(\w+)\s*\(([^)]*)\)')

#         for line in self.lines:
#             trim_line = line.strip()
#             # 跳过空行和单行注释
#             if not trim_line or trim_line.startswith("//"):
#                 continue
#             effective_lines += 1

#             class_match = class_pattern.search(trim_line)
#             if class_match:
#                 class_count += 1
#                 class_names.append(class_match.group(1))

#             method_match = method_pattern.search(trim_line)
#             if method_match:
#                 method_count += 1
#                 methods.append({
#                     "name": method_match.group(2),
#                     "params": method_match.group(3).strip()
#                 })

#         return {
#             "total_lines": total_lines,
#             "effective_lines": effective_lines,
#             "class_count": class_count,
#             "class_names": class_names,
#             "method_count": method_count,
#             "methods": methods,
#             "issues": self.check_simple_issues()
#         }

#     def check_simple_issues(self) -> list:
#         """代码问题扫描：规范 + 安全 + 性能，返回问题列表"""
#         issues = []

#         # ========== 1. 安全漏洞：硬编码敏感信息 ==========
#         sensitive_pattern = re.compile(
#             r'(password|passwd|pwd|secret|token|api_key)\s*=\s*["\']',
#             re.IGNORECASE
#         )
#         for i, line in enumerate(self.lines, 1):
#             if sensitive_pattern.search(line):
#                 issues.append(f"第{i}行：硬编码敏感信息，存在泄露风险")

#         # ========== 2. 代码规范：控制台打印（生产环境禁止） ==========
#         print_pattern = re.compile(r'System\.out\.(print|println)')
#         for i, line in enumerate(self.lines, 1):
#             if print_pattern.search(line):
#                 issues.append(f"第{i}行：使用System.out直接打印，生产环境建议使用日志框架")

#         # ========== 3. 安全漏洞：SQL注入风险（字符串拼接SQL） ==========
#         sql_pattern = re.compile(
#             r'(select|insert|update|delete)\s+.*\+\s*".*"',
#             re.IGNORECASE
#         )
#         for i, line in enumerate(self.lines, 1):
#             if sql_pattern.search(line):
#                 issues.append(f"第{i}行：字符串拼接SQL语句，存在SQL注入风险，建议使用预编译PreparedStatement")

#         # ========== 4. 安全漏洞：命令注入风险 ==========
#         exec_pattern = re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\(.*\+')
#         for i, line in enumerate(self.lines, 1):
#             if exec_pattern.search(line):
#                 issues.append(f"第{i}行：拼接字符串执行系统命令，存在命令注入风险")

#         # ========== 5. 代码规范：魔法值 ==========
#         magic_pattern = re.compile(r'\b(\d{3,})\b')
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("//") or "final" in trim_line:
#                 continue
#             match = magic_pattern.search(trim_line)
#             if match and "for" not in trim_line and "while" not in trim_line:
#                 issues.append(f"第{i}行：存在魔法值「{match.group(1)}」，建议定义为常量")

#         # ========== 6. 代码规范：equals写法空指针风险 ==========
#         equals_pattern = re.compile(r'\b(\w+)\.equals\s*\(\s*["\']')
#         for i, line in enumerate(self.lines, 1):
#             if equals_pattern.search(line):
#                 issues.append(f"第{i}行：变量调用equals可能触发空指针，建议常量在前：\"xxx\".equals(var)")

#         # ========== 7. 并发隐患：静态SimpleDateFormat ==========
#         sdf_pattern = re.compile(r'private\s+static\s+SimpleDateFormat')
#         for i, line in enumerate(self.lines, 1):
#             if sdf_pattern.search(line):
#                 issues.append(f"第{i}行：静态SimpleDateFormat线程不安全，并发场景会出现格式错乱")

#         # ========== 8. 代码规范：catch块吞异常 ==========
#         catch_pattern = re.compile(r'catch\s*\([^)]+\)\s*\{\s*(//.*)?\s*\}')
#         for i, line in enumerate(self.lines, 1):
#             if catch_pattern.search(line):
#                 issues.append(f"第{i}行：空catch块吞异常，建议至少记录错误日志")

#         # ========== 9. 性能隐患：循环内字符串拼接 ==========
#         in_loop = False
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("for ") or trim_line.startswith("while "):
#                 in_loop = True
#                 continue
#             if in_loop and "+" in trim_line and "String" in trim_line and "=" in trim_line:
#                 issues.append(f"第{i}行：循环内使用+拼接字符串，建议使用StringBuilder提升性能")
#             if trim_line == "}":
#                 in_loop = False

#         # ========== 10. 性能隐患：BigDecimal精度丢失 ==========
#         bd_pattern = re.compile(r'new\s+BigDecimal\s*\(\s*\d+\.\d+\s*\)')
#         for i, line in enumerate(self.lines, 1):
#             if bd_pattern.search(line):
#                 issues.append(f"第{i}行：new BigDecimal(double)存在精度丢失，金额计算建议传入字符串")

# #         return issues
# import re


# class JavaCodeAnalyzer:
#     """
#     Java 代码静态分析器
#     支持代码结构解析、规范检查、漏洞检测、性能隐患扫描
#     """

#     def __init__(self, code: str):
#         self.code = code
#         self.lines = code.split("\n")

#     def analyze(self) -> dict:
#         """基础代码结构分析，返回结构化结果"""
#         total_lines = len(self.lines)
#         effective_lines = 0
#         class_count = 0
#         class_names = []
#         method_count = 0
#         methods = []

#         class_pattern = re.compile(r'\bclass\s+(\w+)')
#         method_pattern = re.compile(r'\b(public|private|protected)\s+\w+\s+(\w+)\s*\(([^)]*)\)')

#         for line in self.lines:
#             trim_line = line.strip()
#             # 跳过空行和单行注释
#             if not trim_line or trim_line.startswith("//"):
#                 continue
#             effective_lines += 1

#             class_match = class_pattern.search(trim_line)
#             if class_match:
#                 class_count += 1
#                 class_names.append(class_match.group(1))

#             method_match = method_pattern.search(trim_line)
#             if method_match:
#                 method_count += 1
#                 methods.append({
#                     "name": method_match.group(2),
#                     "params": method_match.group(3).strip()
#                 })

#         return {
#             "total_lines": total_lines,
#             "effective_lines": effective_lines,
#             "class_count": class_count,
#             "class_names": class_names,
#             "method_count": method_count,
#             "methods": methods,
#             "issues": self.check_simple_issues()
#         }

#     def check_simple_issues(self) -> list:
#         """代码问题扫描：规范 + 安全 + 性能，返回问题列表"""
#         issues = []

#         # ==================== 安全漏洞类 ====================

#         # 1. 硬编码敏感信息
#         sensitive_pattern = re.compile(
#             r'(password|passwd|pwd|secret|token|api_key)\s*=\s*["\']',
#             re.IGNORECASE
#         )
#         for i, line in enumerate(self.lines, 1):
#             if sensitive_pattern.search(line):
#                 issues.append(f"第{i}行：硬编码敏感信息，存在泄露风险")

#         # 2. SQL注入风险
#         sql_pattern = re.compile(
#             r'(select|insert|update|delete)\s+.*\+\s*".*"',
#             re.IGNORECASE
#         )
#         for i, line in enumerate(self.lines, 1):
#             if sql_pattern.search(line):
#                 issues.append(f"第{i}行：字符串拼接SQL语句，存在SQL注入风险，建议使用预编译PreparedStatement")

#         # 3. 命令注入风险
#         exec_pattern = re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\(.*\+')
#         for i, line in enumerate(self.lines, 1):
#             if exec_pattern.search(line):
#                 issues.append(f"第{i}行：拼接字符串执行系统命令，存在命令注入风险")

#         # 4. 反序列化漏洞（高危）
#         deserialize_pattern = re.compile(r'ObjectInputStream.*readObject\(\)')
#         for i, line in enumerate(self.lines, 1):
#             if deserialize_pattern.search(line):
#                 issues.append(f"第{i}行：使用readObject反序列化，存在高危远程代码执行漏洞")

#         # 5. 路径遍历风险
#         path_traversal_pattern = re.compile(r'new\s+File\s*\(.*\+')
#         for i, line in enumerate(self.lines, 1):
#             if path_traversal_pattern.search(line):
#                 issues.append(f"第{i}行：拼接字符串构造文件路径，存在路径遍历漏洞风险")

#         # 6. 弱随机数（非密码安全）
#         weak_random_pattern = re.compile(r'new\s+Random\s*\(')
#         for i, line in enumerate(self.lines, 1):
#             if weak_random_pattern.search(line):
#                 issues.append(f"第{i}行：使用Random生成随机数，非密码安全，敏感场景建议用SecureRandom")

#         # 7. 明文密码比较
#         pwd_compare_pattern = re.compile(r'password.*equals\s*\(|equals\s*\(.*password')
#         for i, line in enumerate(self.lines, 1):
#             if pwd_compare_pattern.search(line):
#                 issues.append(f"第{i}行：明文比较密码，建议使用哈希算法（如BCrypt）校验")

#         # ==================== 代码规范类 ====================

#         # 8. 控制台打印
#         print_pattern = re.compile(r'System\.out\.(print|println)')
#         for i, line in enumerate(self.lines, 1):
#             if print_pattern.search(line):
#                 issues.append(f"第{i}行：使用System.out直接打印，生产环境建议使用日志框架")

#         # 9. equals空指针风险
#         equals_pattern = re.compile(r'\b(\w+)\.equals\s*\(\s*["\']')
#         for i, line in enumerate(self.lines, 1):
#             if equals_pattern.search(line):
#                 issues.append(f"第{i}行：变量调用equals可能触发空指针，建议常量在前：\"xxx\".equals(var)")

#         # 10. 静态SimpleDateFormat并发隐患
#         sdf_pattern = re.compile(r'private\s+static\s+SimpleDateFormat')
#         for i, line in enumerate(self.lines, 1):
#             if sdf_pattern.search(line):
#                 issues.append(f"第{i}行：静态SimpleDateFormat线程不安全，并发场景会出现格式错乱")

#         # 11. 空catch块吞异常
#         catch_pattern = re.compile(r'catch\s*\([^)]+\)\s*\{\s*(//.*)?\s*\}')
#         for i, line in enumerate(self.lines, 1):
#             if catch_pattern.search(line):
#                 issues.append(f"第{i}行：空catch块吞异常，建议至少记录错误日志")

#         # 12. 魔法值
#         magic_pattern = re.compile(r'\b(\d{3,})\b')
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("//") or "final" in trim_line:
#                 continue
#             match = magic_pattern.search(trim_line)
#             if match and "for" not in trim_line and "while" not in trim_line:
#                 issues.append(f"第{i}行：存在魔法值「{match.group(1)}」，建议定义为常量")

#         # 13. 方法行数过长
#         self._check_method_length(issues)

#         # 14. 缺省访问修饰符
#         modifier_pattern = re.compile(r'^\s*(class|void|int|String|boolean)\s+\w+')
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("//"):
#                 continue
#             if modifier_pattern.match(trim_line) and "class" not in trim_line[:5]:
#                 issues.append(f"第{i}行：方法缺省访问修饰符，建议明确public/private")

#         # ==================== 性能隐患类 ====================

#         # 15. 循环内字符串拼接
#         in_loop = False
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("for ") or trim_line.startswith("while "):
#                 in_loop = True
#                 continue
#             if in_loop and "+" in trim_line and "String" in trim_line and "=" in trim_line:
#                 issues.append(f"第{i}行：循环内使用+拼接字符串，建议使用StringBuilder提升性能")
#             if trim_line == "}":
#                 in_loop = False

#         # 16. BigDecimal精度丢失
#         bd_pattern = re.compile(r'new\s+BigDecimal\s*\(\s*\d+\.\d+\s*\)')
#         for i, line in enumerate(self.lines, 1):
#             if bd_pattern.search(line):
#                 issues.append(f"第{i}行：new BigDecimal(double)存在精度丢失，金额计算建议传入字符串")

#         # 17. 集合未指定初始容量
#         collection_init_pattern = re.compile(r'new\s+(ArrayList|HashMap|HashSet)\s*\(\)')
#         for i, line in enumerate(self.lines, 1):
#             if collection_init_pattern.search(line):
#                 issues.append(f"第{i}行：集合初始化未指定容量，数据量大时频繁扩容影响性能")

#         # 18. 循环内编译正则
#         in_loop = False
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("for ") or trim_line.startswith("while "):
#                 in_loop = True
#                 continue
#             if in_loop and "Pattern.compile" in trim_line:
#                 issues.append(f"第{i}行：循环内重复编译正则表达式，建议提取为静态常量")
#             if trim_line == "}":
#                 in_loop = False

#         # 19. 不必要的装箱拆箱
#         box_pattern = re.compile(r'new\s+(Integer|Long|Double|Boolean)\s*\(\s*\w+\s*\)')
#         for i, line in enumerate(self.lines, 1):
#             if box_pattern.search(line):
#                 issues.append(f"第{i}行：手动装箱创建包装类，建议使用自动装箱或valueOf")

#         # 20. 循环内重复创建字符串
#         in_loop = False
#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if trim_line.startswith("for ") or trim_line.startswith("while "):
#                 in_loop = True
#                 continue
#             if in_loop and "new String" in trim_line:
#                 issues.append(f"第{i}行：循环内重复创建String对象，产生冗余内存开销")
#             if trim_line == "}":
#                 in_loop = False

#         return issues

#     def _check_method_length(self, issues: list):
#         """检查方法行数，超过50行提示"""
#         method_start = -1
#         brace_count = 0
#         in_method = False
#         current_method_name = ""

#         method_pattern = re.compile(r'\b(public|private|protected)\s+\w+\s+(\w+)\s*\(')

#         for i, line in enumerate(self.lines, 1):
#             trim_line = line.strip()
#             if not in_method:
#                 match = method_pattern.search(trim_line)
#                 if match:
#                     in_method = True
#                     method_start = i
#                     current_method_name = match.group(2)
#                     brace_count = 0
#             else:
#                 brace_count += line.count("{")
#                 brace_count -= line.count("}")
#                 if brace_count <= 0 and "}" in line:
#                     method_lines = i - method_start + 1
#                     if method_lines > 50:
#                         issues.append(f"第{method_start}行：方法「{current_method_name}」行数过多（{method_lines}行），建议拆分")
#                     in_method = False
import re


class JavaCodeAnalyzer:
    """
    Java 代码静态分析器
    支持代码结构解析、规范检查、漏洞检测、性能隐患扫描
    覆盖基础语法、Spring框架、资源管理、并发规范四大维度
    """

    def __init__(self, code: str):
        self.code = code
        self.lines = code.split("\n")

    def analyze(self) -> dict:
        """基础代码结构分析，返回结构化结果"""
        total_lines = len(self.lines)
        effective_lines = 0
        class_count = 0
        class_names = []
        method_count = 0
        methods = []

        class_pattern = re.compile(r'\bclass\s+(\w+)')
        method_pattern = re.compile(r'\b(public|private|protected)\s+\w+\s+(\w+)\s*\(([^)]*)\)')

        for line in self.lines:
            trim_line = line.strip()
            # 跳过空行和单行注释
            if not trim_line or trim_line.startswith("//"):
                continue
            effective_lines += 1

            class_match = class_pattern.search(trim_line)
            if class_match:
                class_count += 1
                class_names.append(class_match.group(1))

            method_match = method_pattern.search(trim_line)
            if method_match:
                method_count += 1
                methods.append({
                    "name": method_match.group(2),
                    "params": method_match.group(3).strip()
                })

        return {
            "total_lines": total_lines,
            "effective_lines": effective_lines,
            "class_count": class_count,
            "class_names": class_names,
            "method_count": method_count,
            "methods": methods,
            "issues": self.check_simple_issues()
        }

    def check_simple_issues(self) -> list:
        """代码问题扫描：规范 + 安全 + 性能 + 框架，返回问题列表"""
        issues = []

        # ==================== 一、安全漏洞类 ====================

        # 1. 硬编码敏感信息
        sensitive_pattern = re.compile(
            r'(password|passwd|pwd|secret|token|api_key)\s*=\s*["\']',
            re.IGNORECASE
        )
        for i, line in enumerate(self.lines, 1):
            if sensitive_pattern.search(line):
                issues.append(f"第{i}行：硬编码敏感信息，存在泄露风险")

        # 2. SQL注入风险
        sql_pattern = re.compile(
            r'(select|insert|update|delete)\s+.*\+\s*".*"',
            re.IGNORECASE
        )
        for i, line in enumerate(self.lines, 1):
            if sql_pattern.search(line):
                issues.append(f"第{i}行：字符串拼接SQL语句，存在SQL注入风险，建议使用预编译PreparedStatement")

        # 3. 命令注入风险
        exec_pattern = re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\(.*\+')
        for i, line in enumerate(self.lines, 1):
            if exec_pattern.search(line):
                issues.append(f"第{i}行：拼接字符串执行系统命令，存在命令注入风险")

        # 4. 反序列化漏洞（高危）
        deserialize_pattern = re.compile(r'ObjectInputStream.*readObject\(\)')
        for i, line in enumerate(self.lines, 1):
            if deserialize_pattern.search(line):
                issues.append(f"第{i}行：使用readObject反序列化，存在高危远程代码执行漏洞")

        # 5. 路径遍历风险
        path_traversal_pattern = re.compile(r'new\s+File\s*\(.*\+')
        for i, line in enumerate(self.lines, 1):
            if path_traversal_pattern.search(line):
                issues.append(f"第{i}行：拼接字符串构造文件路径，存在路径遍历漏洞风险")

        # 6. 弱随机数（非密码安全）
        weak_random_pattern = re.compile(r'new\s+Random\s*\(')
        for i, line in enumerate(self.lines, 1):
            if weak_random_pattern.search(line):
                issues.append(f"第{i}行：使用Random生成随机数，非密码安全，敏感场景建议用SecureRandom")

        # 7. 明文密码比较
        pwd_compare_pattern = re.compile(r'password.*equals\s*\(|equals\s*\(.*password')
        for i, line in enumerate(self.lines, 1):
            if pwd_compare_pattern.search(line):
                issues.append(f"第{i}行：明文比较密码，建议使用哈希算法（如BCrypt）校验")

        # ==================== 二、Spring 框架专属 ====================

        # 8. @Transactional 事务失效（私有方法）
        for i, line in enumerate(self.lines, 1):
            if '@Transactional' in line and i < len(self.lines):
                next_line = self.lines[i]
                if 'private ' in next_line:
                    issues.append(f"第{i}行：@Transactional标注在private方法上，事务失效")

        # 9. @Autowired 字段注入（不推荐）
        for i, line in enumerate(self.lines, 1):
            if '@Autowired' in line and i < len(self.lines):
                next_line = self.lines[i]
                if 'private ' in next_line and ';' in next_line:
                    issues.append(f"第{i}行：@Autowired字段注入，建议使用构造注入提升可测试性")

        # 10. Controller 层直接写业务逻辑
        controller_flag = False
        for i, line in enumerate(self.lines, 1):
            if '@RestController' in line or '@Controller' in line:
                controller_flag = True
                continue
            if controller_flag:
                if 'class ' in line:
                    continue
                if any(k in line for k in ['if(', 'for(', 'while(', 'try{', 'sql', 'insert', 'select']):
                    issues.append(f"第{i}行：Controller层直接编写业务逻辑，建议下沉到Service层")
                    break

        # 11. @Value 零散配置注入
        value_pattern = re.compile(r'@Value\s*\(\$\{')
        value_count = 0
        for i, line in enumerate(self.lines, 1):
            if value_pattern.search(line):
                value_count += 1
        if value_count >= 3:
            issues.append(f"代码中存在{value_count}处@Value零散注入，建议封装为配置类统一管理")

        # ==================== 三、代码规范类 ====================

        # 12. 控制台打印
        print_pattern = re.compile(r'System\.out\.(print|println)')
        for i, line in enumerate(self.lines, 1):
            if print_pattern.search(line):
                issues.append(f"第{i}行：使用System.out直接打印，生产环境建议使用日志框架")

        # 13. equals空指针风险
        equals_pattern = re.compile(r'\b(\w+)\.equals\s*\(\s*["\']')
        for i, line in enumerate(self.lines, 1):
            if equals_pattern.search(line):
                issues.append(f"第{i}行：变量调用equals可能触发空指针，建议常量在前：\"xxx\".equals(var)")

        # 14. 静态SimpleDateFormat并发隐患
        sdf_pattern = re.compile(r'private\s+static\s+SimpleDateFormat')
        for i, line in enumerate(self.lines, 1):
            if sdf_pattern.search(line):
                issues.append(f"第{i}行：静态SimpleDateFormat线程不安全，并发场景会出现格式错乱")

        # 15. 空catch块吞异常
        catch_pattern = re.compile(r'catch\s*\([^)]+\)\s*\{\s*(//.*)?\s*\}')
        for i, line in enumerate(self.lines, 1):
            if catch_pattern.search(line):
                issues.append(f"第{i}行：空catch块吞异常，建议至少记录错误日志")

        # 16. 魔法值
        magic_pattern = re.compile(r'\b(\d{3,})\b')
        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if trim_line.startswith("//") or "final" in trim_line:
                continue
            match = magic_pattern.search(trim_line)
            if match and "for" not in trim_line and "while" not in trim_line:
                issues.append(f"第{i}行：存在魔法值「{match.group(1)}」，建议定义为常量")

        # 17. 方法行数过长
        self._check_method_length(issues)

        # 18. 缺省访问修饰符
        modifier_pattern = re.compile(r'^\s*(void|int|String|boolean)\s+\w+')
        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if trim_line.startswith("//"):
                continue
            if modifier_pattern.match(trim_line):
                issues.append(f"第{i}行：方法缺省访问修饰符，建议明确public/private")

        # 19. 重写equals没重写hashCode
        has_equals = False
        has_hashcode = False
        for line in self.lines:
            if 'public boolean equals(Object' in line:
                has_equals = True
            if 'public int hashCode()' in line:
                has_hashcode = True
        if has_equals and not has_hashcode:
            issues.append("重写了equals方法但未重写hashCode，集合操作会出现逻辑错误")

        # ==================== 四、资源与并发规范 ====================

        # 20. 流/连接资源未关闭
        resource_pattern = re.compile(r'new\s+(FileInputStream|FileOutputStream|Connection|Statement|ResultSet)\s*\(')
        has_try_resource = False
        for line in self.lines:
            if 'try (' in line:
                has_try_resource = True
                break
        if not has_try_resource:
            for i, line in enumerate(self.lines, 1):
                if resource_pattern.search(line):
                    issues.append(f"第{i}行：资源未使用try-with-resources自动关闭，存在资源泄露风险")
                    break

        # 21. Arrays.asList 后修改列表
        aslist_pattern = re.compile(r'Arrays\.asList\(')
        for i, line in enumerate(self.lines, 1):
            if aslist_pattern.search(line):
                for j in range(i, min(i+5, len(self.lines))):
                    if '.add(' in self.lines[j] or '.remove(' in self.lines[j]:
                        issues.append(f"第{i}行：Arrays.asList返回固定大小列表，调用add/remove会抛出UnsupportedOperationException")
                        break

        # 22. 手动 new Thread
        new_thread_pattern = re.compile(r'new\s+Thread\s*\(')
        for i, line in enumerate(self.lines, 1):
            if new_thread_pattern.search(line):
                issues.append(f"第{i}行：手动创建Thread对象，建议使用线程池统一管理，避免OOM")

        # 23. 线程池未指定拒绝策略
        pool_pattern = re.compile(r'new\s+ThreadPoolExecutor\s*\(')
        for i, line in enumerate(self.lines, 1):
            if pool_pattern.search(line) and 'RejectedExecutionHandler' not in line:
                issues.append(f"第{i}行：线程池未指定拒绝策略，高负载下可能导致任务丢失")

        # ==================== 五、性能隐患类 ====================

        # 24. 循环内字符串拼接
        in_loop = False
        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if trim_line.startswith("for ") or trim_line.startswith("while "):
                in_loop = True
                continue
            if in_loop and "+" in trim_line and "String" in trim_line and "=" in trim_line:
                issues.append(f"第{i}行：循环内使用+拼接字符串，建议使用StringBuilder提升性能")
            if trim_line == "}":
                in_loop = False

        # 25. BigDecimal精度丢失
        bd_pattern = re.compile(r'new\s+BigDecimal\s*\(\s*\d+\.\d+\s*\)')
        for i, line in enumerate(self.lines, 1):
            if bd_pattern.search(line):
                issues.append(f"第{i}行：new BigDecimal(double)存在精度丢失，金额计算建议传入字符串")

        # 26. 集合未指定初始容量
        collection_init_pattern = re.compile(r'new\s+(ArrayList|HashMap|HashSet)\s*\(\)')
        for i, line in enumerate(self.lines, 1):
            if collection_init_pattern.search(line):
                issues.append(f"第{i}行：集合初始化未指定容量，数据量大时频繁扩容影响性能")

        # 27. 循环内编译正则
        in_loop = False
        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if trim_line.startswith("for ") or trim_line.startswith("while "):
                in_loop = True
                continue
            if in_loop and "Pattern.compile" in trim_line:
                issues.append(f"第{i}行：循环内重复编译正则表达式，建议提取为静态常量")
            if trim_line == "}":
                in_loop = False

        # 28. 不必要的装箱拆箱
        box_pattern = re.compile(r'new\s+(Integer|Long|Double|Boolean)\s*\(\s*\w+\s*\)')
        for i, line in enumerate(self.lines, 1):
            if box_pattern.search(line):
                issues.append(f"第{i}行：手动装箱创建包装类，建议使用自动装箱或valueOf")

        # 29. 循环内重复创建字符串
        in_loop = False
        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if trim_line.startswith("for ") or trim_line.startswith("while "):
                in_loop = True
                continue
            if in_loop and "new String" in trim_line:
                issues.append(f"第{i}行：循环内重复创建String对象，产生冗余内存开销")
            if trim_line == "}":
                in_loop = False

        # 30. 日志拼接字符串（未用占位符）
        log_pattern = re.compile(r'log\.(info|debug|error|warn)\s*\(.*\+')
        for i, line in enumerate(self.lines, 1):
            if log_pattern.search(line):
                issues.append(f"第{i}行：日志使用字符串拼接，建议使用占位符{{}}提升性能")

        return issues

    def _check_method_length(self, issues: list):
        """检查方法行数，超过50行提示"""
        method_start = -1
        brace_count = 0
        in_method = False
        current_method_name = ""

        method_pattern = re.compile(r'\b(public|private|protected)\s+\w+\s+(\w+)\s*\(')

        for i, line in enumerate(self.lines, 1):
            trim_line = line.strip()
            if not in_method:
                match = method_pattern.search(trim_line)
                if match:
                    in_method = True
                    method_start = i
                    current_method_name = match.group(2)
                    brace_count = 0
            else:
                brace_count += line.count("{")
                brace_count -= line.count("}")
                if brace_count <= 0 and "}" in line:
                    method_lines = i - method_start + 1
                    if method_lines > 50:
                        issues.append(f"第{method_start}行：方法「{current_method_name}」行数过多（{method_lines}行），建议拆分")
                    in_method = False
