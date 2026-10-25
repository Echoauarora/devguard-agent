# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from code_analyzer import JavaCodeAnalyzer


# class ToolRegistry:
#     """
#     工具注册表
#     统一管理所有工具，提供工具定义给大模型，执行工具调用
#     """

#     def __init__(self):
#         self.tools = {
#             "java_code_scan": self.java_code_scan,
#             "java_code_structure": self.java_code_structure
#         }

#     def get_tool_definitions(self) -> list:
#         """
#         获取所有工具的 OpenAI 格式定义，传给大模型
#         """
#         return [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "java_code_scan",
#                     "description": "扫描 Java 源代码，检测其中的安全漏洞、代码规范问题、性能隐患，返回问题列表和风险说明。",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "code": {
#                                 "type": "string",
#                                 "description": "要扫描的 Java 源代码内容"
#                             }
#                         },
#                         "required": ["code"]
#                     }
#                 }
#             },
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "java_code_structure",
#                     "description": "统计Java代码的基本结构信息，包括总行数，有效行数，类数量，方法数量，类名列表",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "code": {
#                                 "type": "string",
#                                 "description": "要统计的java源代码内容"
#                             }
#                         },
#                         "required": ["code"]
#                     }
#                 }
#             }
#         ]

#     def execute_tool(self, tool_name: str, arguments: dict) -> str:
#         """
#         根据工具名执行工具，返回结果字符串
#         """
#         if tool_name not in self.tools:
#             return f"错误：未知工具 {tool_name}"

#         try:
#             result = self.tools[tool_name](**arguments)
#             return str(result)
#         except Exception as e:
#             return f"工具执行异常：{str(e)}"

#     def java_code_scan(self, code: str) -> list:
#         """
#         Java 代码静态扫描工具
#         """
#         analyzer = JavaCodeAnalyzer(code)
#         result = analyzer.analyze()
#         return result.get("issues", [])

#     def java_code_structure(self,code: str)-> dict:
#         """
#         java 代码结构统计工具
#         """
#         analyzer = JavaCodeAnalyzer(code)
#         result = analyzer.analyzer()
#         return{
#             "total_lines": result["total_lines"],
#             "effective_lines": result["effective_lines"],
#             "class_count": result["class_count"],
#             "class_names": result["class_names"],
#             "method_count": result["method_count"]
#         }
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_analyzer import JavaCodeAnalyzer


class ToolRegistry:
    """
    工具注册表
    统一管理所有工具，提供工具定义给大模型，执行工具调用
    """

    def __init__(self):
        self.tools = {
            "java_code_scan": self.java_code_scan,
            "java_code_structure": self.java_code_structure
        }

    def get_tool_definitions(self) -> list:
        """
        获取所有工具的 OpenAI 格式定义，传给大模型
        """
        return [
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

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        根据工具名执行工具，返回结果字符串
        """
        if tool_name not in self.tools:
            return f"【工具执行失败】未知工具：{tool_name}"

        try:
            result = self.tools[tool_name](**arguments)
            return f"【工具执行成功】\n{str(result)}"
        except Exception as e:
            return f"【工具执行失败】{str(e)}"

    # ========== 工具实现 ==========

    def java_code_scan(self, code: str) -> list:
        """
        Java 代码静态扫描工具
        """
        analyzer = JavaCodeAnalyzer(code)
        result = analyzer.analyze()
        return result.get("issues", [])

    def java_code_structure(self, code: str) -> dict:
        """
        Java 代码结构统计工具
        """
        analyzer = JavaCodeAnalyzer(code)
        result = analyzer.analyze()
        return {
            "total_lines": result["total_lines"],
            "effective_lines": result["effective_lines"],
            "class_count": result["class_count"],
            "class_names": result["class_names"],
            "method_count": result["method_count"]
        }
