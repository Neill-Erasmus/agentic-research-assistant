import json
import os
import re
import requests

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/chat')
MODEL = os.getenv('OLLAMA_MODEL', 'llama3')

def _ollama_timeout_seconds() -> float:
    """
    Define the timeout for Ollama requests.

    Returns:
        float: The timeout in seconds.
    """    
    
    raw_value = os.getenv('OLLAMA_TIMEOUT_SECONDS') or os.getenv('OLLAMA_TIMEOUT') or '180'
    try:
        return max(15.0, float(raw_value))
    except ValueError:
        return 180.0

OLLAMA_TIMEOUT_SECONDS = _ollama_timeout_seconds()

class BaseAgent:
    """
    This class represents a base agent that can interact with the Ollama LLM.
    It provides common functionality for sending messages, handling tool calls, and defining a system prompt.
    Subclasses can implement specific agents with their own prompts and tools by inheriting from this base class.
    """    
    
    def __init__(self, name: str, system_prompt: str, tools: list[dict]):
        """
        Initialize the base agent.

        Args:
            name (str): The name of the agent.
            system_prompt (str): The system prompt for the agent.
            tools (list[dict]): A list of available tools for the agent.
        """        
        
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self._http = requests.Session()

    def _chat(self, messages: list[dict]) -> dict | None:
        """
        Send messages to Ollama and return the response dict, or None on failure.

        Args:
            messages (list[dict]): A list of message dicts to send to the LLM, typically including a system prompt and user input.

        Returns:
            dict | None: The response from Ollama as a dict, or None if there was an error or timeout.
        """        
        
        payload = {
            'model': MODEL,
            'messages': messages,
            'stream': False,
        }
        try:
            response = self._http.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            if 'message' not in data or 'content' not in data.get('message', {}):
                print(f' [{self.name}] LLM response missing expected message content.')
                return None
            return data
        except requests.Timeout as exc:
            print(
                f' [{self.name}] Ollama request timed out after {OLLAMA_TIMEOUT_SECONDS:.0f}s: {exc}. '
                'Try a smaller prompt or increase OLLAMA_TIMEOUT_SECONDS.'
            )
            return None
        except requests.RequestException as exc:
            print(f' [{self.name}] Could not reach Ollama at {OLLAMA_URL}: {exc}')
            return None
        except ValueError:
            print(f' [{self.name}] Ollama returned non-JSON response.')
            return None

    def _build_tool_prompt(self) -> str:
        """
        Build a prompt section describing the available tools and how to call them.

        Returns:
            str: The tool prompt.
        """        
        
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
        """
        Parse a tool call from the agent's response text. The expected format is a JSON object with "tool" and "args" keys, optionally wrapped in markdown code fences.

        Args:
            text (str): The text to parse.

        Returns:
            dict | None: The parsed tool call, or None if the text is not a valid tool call.
        """        
        
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