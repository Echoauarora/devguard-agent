from openai import OpenAI
import os
import time


class LLMClient:

    def __init__(self):
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("LLM_MODEL", "deepseek-flash")

        if not api_key:
            raise ValueError("请设置环境变量 LLM_API_KEY")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=2,
        )

    def chat(self, prompt: str, system_prompt: str = "你是一个代码工程专家。") -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def chat_with_function(self, messages: list, tools: list) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        message = response.choices[0].message

        tool_calls = None
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": str(tc.id),
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })

        content = message.content if message.content is not None else ""

        return {
            "role": message.role,
            "content": message.content,
            "tool_calls": tool_calls
        }