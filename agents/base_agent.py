import json
import os
import re
import requests

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/chat')
MODEL = os.getenv('OLLAMA_MODEL', 'llama3')

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: list[dict]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self._http = requests.Session()

    def _chat(self, messages: list[dict]) -> dict | None:
        """Send messages to Ollama and return the response dict, or None on failure."""
        payload = {
            'model': MODEL,
            'messages': messages,
            'stream': False,
        }
        try:
            response = self._http.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'message' not in data or 'content' not in data.get('message', {}):
                print(f' [{self.name}] LLM response missing expected message content.')
                return None
            return data
        except requests.RequestException as exc:
            print(f' [{self.name}] Could not reach Ollama at {OLLAMA_URL}: {exc}')
            return None
        except ValueError:
            print(f' [{self.name}] Ollama returned non-JSON response.')
            return None

    def _build_tool_prompt(self) -> str:
        """Describe tools to the model in the system prompt."""
        if not self.tools:
            return ''
        lines = [
            '\n\nYou have access to the following tools.',
            'To call a tool, respond ONLY with valid JSON in this format:',
            '{"tool": "<tool_name>", "args": {<key: value>}}',
            'Available tools:'
        ]
        for t in self.tools:
            lines.append(f' - {t["name"]}: {t["description"]}')
            lines.append(f'   Parameters: {t["params"]}')
        return '\n'.join(lines)

    def _parse_tool_call(self, text: str) -> dict | None:
        """Try to parse the model response as a tool call JSON."""
        if not text:
            return None

        clean = text.strip()
        fenced_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean, flags=re.DOTALL)
        if fenced_match:
            clean = fenced_match.group(1)

        try:
            if clean.startswith('{'):
                data = json.loads(clean)
                if 'tool' in data and 'args' in data:
                    return data
        except json.JSONDecodeError:
            return None
        return None