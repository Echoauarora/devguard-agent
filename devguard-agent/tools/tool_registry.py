import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.structured_analyzer import JavaStructuredAnalyzer


class ToolRegistry:

    def __init__(self, task_id=None, backend_base="http://localhost:8080/api"):
        self.task_id = task_id
        self.backend_base = backend_base
        self.tools = {
            "java_code_scan": self.java_code_scan,
            "java_code_structure": self.java_code_structure,
            "project_list_files": self.project_list_files,
            "project_read_file": self.project_read_file
        }

    def get_tool_definitions(self, project_mode=False) -> list:
        snippet_tools = [
            {
                "type": "function",
                "function": {
                    "name": "java_code_structure",
                    "description": "统计 Java 代码的基本结构信息，包括总行数、有效行数、类数量、方法数量、类名列表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要统计的 Java 源代码内容"
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "java_code_scan",
                    "description": "扫描 Java 源代码，检测其中的安全漏洞、代码规范问题、性能隐患，返回问题列表和风险说明。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要扫描的 Java 源代码内容"
                            }
                        },
                        "required": ["code"]
                    }
                }
            }
        ]
        project_tools = snippet_tools + [
            {
                "type": "function",
                "function": {
                    "name": "project_list_files",
                    "description": "列出当前工程所有可分析的源码文件（相对路径列表），用于了解工程结构和选择要深入分析的文件。无需参数。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "project_read_file",
                    "description": "读取指定工程源码文件的完整内容，用于深入分析单个文件的安全漏洞和代码质量。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filePath": {
                                "type": "string",
                                "description": "文件相对路径，如 'src/main/java/com/example/UserController.java'"
                            },
                            "maxChars": {
                                "type": "integer",
                                "description": "最大读取字符数，默认50000，防止单文件过大"
                            }
                        },
                        "required": ["filePath"]
                    }
                }
            }
        ]
        return project_tools if project_mode else snippet_tools

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name not in self.tools:
            return "[工具执行失败] 未知工具: " + tool_name
        try:
            result = self.tools[tool_name](**arguments)
            return "[工具执行成功]\n" + str(result)
        except Exception as e:
            return "[工具执行失败] " + str(e)

    def java_code_scan(self, code: str, **kwargs) -> list:
        try:
            analyzer = JavaStructuredAnalyzer(code)
            return analyzer.get_security_findings().get("findings", [])
        except Exception as e:
            return [{"severity": "ERROR", "detail": "分析失败: " + str(e)}]

    def java_code_structure(self, code: str, **kwargs) -> dict:
        try:
            analyzer = JavaStructuredAnalyzer(code)
            return analyzer.get_structure_report()
        except Exception as e:
            return {"error": str(e), "totalLines": len(code.split("\n"))}

    def _api_get(self, path):
        import urllib.request, json
        try:
            resp = urllib.request.urlopen(self.backend_base + path, timeout=15)
            return json.loads(resp.read().decode())
        except Exception as e:
            return {"code": 500, "msg": str(e)}

    def project_list_files(self, **kwargs) -> list:
        if not self.task_id:
            return ["[error] project_list_files 需要 task_id"]
        data = self._api_get("/task/project/list-files?taskId=" + str(self.task_id))
        if data and data.get("code") == 200:
            return data.get("data", [])
        return ["[error] " + str(data.get("msg", "unknown"))]

    def project_read_file(self, filePath: str, maxChars: int = 50000, **kwargs) -> str:
        if not self.task_id:
            return "[error] project_read_file 需要 task_id"
        import urllib.parse
        url = "/task/project/read-file?taskId=" + str(self.task_id) +               "&filePath=" + urllib.parse.quote(filePath) +               "&maxChars=" + str(maxChars)
        data = self._api_get(url)
        if data and data.get("code") == 200:
            return data.get("data", "")
        return "[error] " + str(data.get("msg", "unknown"))