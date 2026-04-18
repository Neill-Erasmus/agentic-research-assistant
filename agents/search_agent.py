from agents.base_agent import BaseAgent
import re
from tools.web_search import web_search

TOOLS = [
    {
        'name': 'web_search',
        'description': 'Search the web for information on a topic.',
        'params': '{"query": "string"}'
    }
]

class SearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name='SearchAgent',
            system_prompt=(
                'You are a research search specialist. '
                'When given a research topic, formulate a good search query '
                'and call the web_search tool.' + self._build_tool_prompt_static(TOOLS)
            ),
            tools=TOOLS
        )

    def _build_tool_prompt_static(self, tools):
        lines = [
            '\n\nYou have access to the following tools.',
            'To call a tool, respond ONLY with valid JSON:',
            '{"tool": "<name>", "args": {<params>}}',
            'Available tools:'
        ]
        for t in tools:
            lines.append(f' - {t["name"]}: {t["description"]}')
        return '\n'.join(lines)

    def _normalise_topic(self, topic: str) -> str:
        """Clean common instruction phrasing so search terms stay focused."""
        cleaned = topic.strip()
        prefixes = (
            'research ',
            'find information about ',
            'tell me about ',
            'what is ',
            'who is ',
        )
        lowered = cleaned.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break

        works_pattern = re.compile(
            r'(?i)^(.+?)\s+and\s+what\s+(?:his|her|their|the)\s+main\s+works\s+were[?.!]*$'
        )
        if works_pattern.match(cleaned):
            cleaned = works_pattern.sub(r'\1 main works', cleaned)
        else:
            cleaned = re.sub(r'(?i)\band\s+what\b.*$', '', cleaned)

        cleaned = re.sub(r'(?i)^what\s+(?:is|are|was|were)\s+', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.rstrip('?.!') or topic

    def run(self, topic: str) -> list[dict]:
        """Search for a topic and return result list."""
        topic = self._normalise_topic(topic)

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': f'Find information about: {topic}'}
        ]

        response = self._chat(messages)
        if response:
            reply = response['message']['content']
            tool_call = self._parse_tool_call(reply)

            if tool_call and tool_call['tool'] == 'web_search':
                args = tool_call.get('args', {})
                query = args.get('query', topic)
                max_results = args.get('max_results', 8)

                try:
                    max_results = int(max_results)
                except (TypeError, ValueError):
                    max_results = 8

                print(f' [SearchAgent] Calling web_search("{query}")')
                results = web_search(query, max_results=max_results)
                if results:
                    return results
                print(' [SearchAgent] Tool call returned no results. Falling back to direct search.')

        print(f' [SearchAgent] Fallback direct search for: {topic}')
        return web_search(topic, max_results=8)