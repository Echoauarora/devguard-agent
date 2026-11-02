import re
from typing import List, Dict, Optional


class JavaStructuredAnalyzer:
    ANNOTATION_RE = re.compile(r'@(\w+(?:\.\w+)*)\s*(?:\(([^)]*)\))?')

    CLASS_RE = re.compile(
        r'(public|private|protected)?\s*'
        r'(static\s+|abstract\s+|final\s+|strictfp\s+)*'
        r'(class|interface|enum|record)\s+'
        r'(\w+)\s*'
        r'(?:<[^>]*>)?\s*'
        r'(?:extends\s+[\w<>,\s]+)?\s*'
        r'(?:implements\s+[\w<>,\s]+)?\s*\{'
    )

    METHOD_RE = re.compile(
        r'(public|private|protected)\s+'
        r'(static\s+)?(final\s+)?(abstract\s+)?(synchronized\s+)?'
        r'([\w<>\[\],\s]+?)\s+'
        r'(\w+)\s*'
        r'\(([^)]*)\)\s*'
        r'(?:throws\s+[\w,\s]+)?\s*[;{]'
    )

    ANNOTATED_METHOD_RE = re.compile(
        r'((?:@\w+(?:\([^)]*\))?\s+)+)'
        r'(public|private|protected)\s+'
        r'(static\s+)?(final\s+)?(synchronized\s+)?'
        r'([\w<>\[\],\s]+?)\s+'
        r'(\w+)\s*\(([^)]*)\)'
    )

    FIELD_RE = re.compile(
        r'(public|private|protected)\s+'
        r'(static\s+)?(final\s+)?(transient\s+|volatile\s+)?'
        r'([\w<>\[\],\s]+?)\s+'
        r'(\w+)\s*(?:=\s*[^;]+)?\s*;'
    )

    SQL_INJECTION_CHECKS = [
        (re.compile(r'\.createStatement\(\)'), '使用Statement而非PreparedStatement'),
        (re.compile(r'executeQuery\s*\(\s*"[^"]*"\s*\+'), 'SQL字符串拼接（executeQuery）'),
        (re.compile(r'executeUpdate\s*\(\s*"[^"]*"\s*\+'), 'SQL字符串拼接（executeUpdate）'),
    ]

    HARDCODED_SECRET_CHECKS = [
        (re.compile(r'(?:password|passwd|pwd|secret|token|api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{4,}["\']', re.I),
         '疑似硬编码密码/密钥'),
    ]

    RESOURCE_LEAK_CHECKS = [
        (re.compile(r'\bnew\s+(Connection|Statement|PreparedStatement|ResultSet|InputStream|FileInputStream|OutputStream|FileOutputStream)\b'),
         '打开资源未使用try-with-resources'),
    ]

    LOGGER_CHECK = re.compile(r'\.printStackTrace\(\)')

    MAGIC_NUMBER_CHECKS = [
        (re.compile(r'\b(0|00000000|11111111|12345678|87654321)\b'), '可能的测试数据/占位数据'),
    ]

    UNUSED_IMPORT_CHECKS = [
        (re.compile(r'import\s+.*\.star\s*;'), '使用通配符import'),
    ]

    def __init__(self, source: str):
        self.source = source
        self.lines = source.split('\n')
        self.classes: List[Dict] = []
        self.methods: List[Dict] = []
        self.fields: List[Dict] = []
        self.imports: List[str] = []
        self.package: Optional[str] = None
        self.issues: List[Dict] = []
        self._extract_all()

    def _extract_all(self):
        self._extract_header()
        self._extract_classes()
        self._extract_fields_and_methods()
        self._scan_security()
        self._scan_quality()

    def _extract_header(self):
        for line in self.lines:
            s = line.strip()
            if s.startswith('package ') and s.endswith(';'):
                self.package = s[8:-1].strip()
            elif s.startswith('import ') and s.endswith(';'):
                self.imports.append(s[7:-1].strip())

    def _extract_classes(self):
        for i, line in enumerate(self.lines):
            m = self.CLASS_RE.search(line.strip())
            if not m:
                continue
            self.classes.append({
                'name': m.group(4),
                'type': m.group(3),
                'modifier': m.group(1) or 'package-private',
                'line': i + 1,
                'methods': [],
                'fields': []
            })

    def _extract_fields_and_methods(self):
        pending_annotations = []

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            ann_m = self.ANNOTATION_RE.search(stripped)
            if stripped.startswith('@') and ann_m:
                pending_annotations.append({
                    'name': ann_m.group(1),
                    'params': ann_m.group(2) or '',
                    'line': i + 1
                })
                continue

            if pending_annotations and stripped and not stripped.startswith('//'):
                am = self.ANNOTATED_METHOD_RE.search(stripped)
                if am:
                    self._add_method(am, [a['name'] for a in pending_annotations], i + 1)
                    pending_annotations = []
                    continue

            mm = self.METHOD_RE.search(stripped)
            if mm:
                self._add_method(mm, [], i + 1)
                pending_annotations = []
                continue

            fm = self.FIELD_RE.search(stripped)
            if fm:
                self._add_field(fm, i + 1)
                pending_annotations = []

    def _add_method(self, m, annotations, line_num):
        g = m.groups()
        if len(g) < 7:
            return

        name = g[6]
        if not name or name in ('if', 'for', 'while', 'switch', 'catch', 'try', 'else', 'return', 'new'):
            return

        ret = (g[5] or '').strip()
        modifier = g[0] or 'package-private'
        params = g[7].strip() if len(g) > 7 else ''

        method = {
            'name': name,
            'modifier': modifier,
            'return_type': ret,
            'params': params,
            'annotations': annotations,
            'line': line_num
        }

        self.methods.append(method)
        if self.classes:
            self.classes[-1]['methods'].append({
                'name': method['name'],
                'modifier': method['modifier'],
                'params': method['params']
            })

    def _add_field(self, m, line_num):
        g = m.groups()
        if len(g) < 6:
            return
        field = {
            'name': g[5],
            'modifier': g[0] or 'package-private',
            'type': (g[4] or '').strip(),
            'is_final': bool(g[2]),
            'line': line_num
        }
        self.fields.append(field)
        if self.classes:
            self.classes[-1]['fields'].append({
                'name': field['name'],
                'type': field['type']
            })

    def _scan_security(self):
        for i, line in enumerate(self.lines):
            s = line.strip()
            line_num = i + 1

            for pat, desc in self.SQL_INJECTION_CHECKS:
                if pat.search(s):
                    self.issues.append({'severity': 'HIGH', 'type': 'SQL_INJECTION', 'line': line_num, 'detail': desc, 'suggestion': '改用PreparedStatement + ?占位符', 'snippet': s[:100]})
                    break

            for pat, desc in self.HARDCODED_SECRET_CHECKS:
                if pat.search(s):
                    self.issues.append({'severity': 'HIGH', 'type': 'HARDCODED_SECRET', 'line': line_num, 'detail': desc, 'suggestion': '移至配置文件或环境变量，用@Value注入', 'snippet': s[:100]})
                    break

            for pat, desc in self.RESOURCE_LEAK_CHECKS:
                if pat.search(s):
                    self.issues.append({'severity': 'MEDIUM', 'type': 'RESOURCE_LEAK', 'line': line_num, 'detail': desc, 'suggestion': '用try-with-resources', 'snippet': s[:100]})

            if self.LOGGER_CHECK.search(s):
                self.issues.append({'severity': 'LOW', 'type': 'BAD_EXCEPTION', 'line': line_num, 'detail': '使用printStackTrace()而非日志框架', 'suggestion': '用log.error("msg", e)', 'snippet': s[:100]})

    def _scan_quality(self):
        for i, line in enumerate(self.lines):
            s = line.strip()
            line_num = i + 1

            for pat, desc in self.MAGIC_NUMBER_CHECKS:
                if pat.search(s) and not s.startswith('//') and not s.startswith('*'):
                    self.issues.append({'severity': 'LOW', 'type': 'MAGIC_NUMBER', 'line': line_num, 'detail': desc, 'suggestion': '定义为常量或枚举', 'snippet': s[:100]})

            for pat, desc in self.UNUSED_IMPORT_CHECKS:
                if pat.search(s):
                    self.issues.append({'severity': 'LOW', 'type': 'CODE_STYLE', 'line': line_num, 'detail': desc, 'suggestion': '显式导入，避免.*', 'snippet': s[:100]})

    def get_structure_report(self) -> Dict:
        total = len(self.lines)
        effective = sum(1 for l in self.lines if l.strip() and not l.strip().startswith('//') and not l.strip().startswith('/*') and not l.strip().startswith('*'))
        by_sev = {'HIGH': sum(1 for i in self.issues if i['severity'] == 'HIGH'), 'MEDIUM': sum(1 for i in self.issues if i['severity'] == 'MEDIUM'), 'LOW': sum(1 for i in self.issues if i['severity'] == 'LOW')}
        return {
            'package': self.package,
            'imports_count': len(self.imports),
            'imports': self.imports[:20],
            'metrics': {'totalLines': total, 'effectiveLines': effective, 'classCount': len(self.classes), 'methodCount': len(self.methods), 'fieldCount': len(self.fields)},
            'classes': [{'name': c['name'], 'type': c['type'], 'modifier': c['modifier'], 'line': c['line'], 'methods': c['methods'], 'fields': c['fields']} for c in self.classes],
            'top_methods': [{'name': m['name'], 'modifier': m['modifier'], 'returnType': m['return_type'] or 'void', 'params': m['params'], 'annotations': m['annotations'], 'line': m['line']} for m in self.methods[:30]],
            'issues_by_severity': by_sev,
            'all_issues_count': len(self.issues)
        }

    def get_security_findings(self) -> Dict:
        by_sev = {'HIGH': sum(1 for i in self.issues if i['severity'] == 'HIGH'), 'MEDIUM': sum(1 for i in self.issues if i['severity'] == 'MEDIUM'), 'LOW': sum(1 for i in self.issues if i['severity'] == 'LOW')}
        score = max(0, 100 - by_sev['HIGH'] * 20 - by_sev['MEDIUM'] * 8 - by_sev['LOW'] * 2)
        return {
            'overallScore': score,
            'summary': self._generate_summary(by_sev),
            'findings': self.issues,
            'stats': by_sev,
            'highlights': {
                'classes': [c['name'] for c in self.classes],
                'risky_imports': [imp for imp in self.imports if any(k in imp.lower() for k in ['sql', 'jdbc', 'io', 'net'])][:10],
                'annotated_methods': [m['name'] + (' @' + ','.join(m['annotations']) if m['annotations'] else '') for m in self.methods if m['annotations']][:10]
            }
        }

    def _generate_summary(self, by_sev) -> str:
        h, m_ = by_sev['HIGH'], by_sev['MEDIUM']
        cls, mtd = len(self.classes), len(self.methods)
        if h > 0:
            return f'共 {cls} 类 {mtd} 方法。存在 {h} 个高危（SQL注入/硬编码密钥），{m_} 个中等。需优先修复！'
        elif m_ > 0:
            return f'代码结构良好（{cls}类{mtd}方法），有 {m_} 个中等问题建议优化。'
        else:
            return f'代码结构清晰（{cls}类{mtd}方法），未发现明显安全问题。质量良好。'