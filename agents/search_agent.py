from agents.base_agent import BaseAgent
import re
from tools.web_search import web_search

TOOLS = [
    {
        'name': 'web_search',
        'description': 'Search the web for information on a topic using DuckDuckGo and Wikipedia.',
        'params': '{"query": "string"}'
    },
    {
        'name': 'tavily_search',
        'description': 'Search the web using Tavily (requires TAVILY_API_KEY). Provides high-relevance results optimised for AI agents.',
        'params': '{"query": "string"}'
    }
]

class SearchAgent(BaseAgent):
    """
    An agent that formulates search queries and calls a web search tool.

    Args:
        BaseAgent (_type_): The base agent class that provides common functionality for all agents, including the chat interface.
    """    
    
    def __init__(self) -> None:
        """
        Initialize the SearchAgent with a system prompt that instructs it to formulate search queries and call the web_search tool.
        The prompt includes a description of the available tools and how to call them.
        """        
        
        super().__init__(
            name='SearchAgent',
            system_prompt=(
                'You are a research search specialist. '
                'When given a research topic, formulate a good search query '
                'and call the web_search tool.' + self._build_tool_prompt_static(TOOLS)
            ),
            tools=TOOLS
        )

    def _build_tool_prompt_static(self, tools : list[dict]) -> str:
        """
        Build a static part of the system prompt that describes the available tools.

        Args:
            self (SearchAgent): The instance of the SearchAgent class.
            tools (list[dict]): A list of tool descriptions, where each tool is a dict with 'name', 'description', and 'params' keys.

        Returns:
            str: A string containing the static part of the system prompt describing the available tools.
        """                
        
        lines = [
            '\n\nYou have access to the following tools.',
            'To call a tool, respond ONLY with valid JSON:',
            '{"tool": "<name>", "args": {<params>}}',
            'Available tools:'
        ]
        for t in tools:
            lines.append(f' - {t["name"]}: {t["description"]}')
        return '\n'.join(lines)

    def _normalise_topic(self, topic : str) -> str:
        """
        Normalise the research topic by stripping common prefixes and suffixes, and simplifying certain patterns.

        Args:
            self (SearchAgent): The instance of the SearchAgent class.
            topic (str): The research topic to normalise.

        Returns:
            str: The normalised research topic.
        """        
        
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

    def run(self, topic : str) -> list[dict]:
        """
        Search for a topic and return result list.

        Args:
            self (SearchAgent): The instance of the SearchAgent class.
            topic (str): The research topic to search for.

        Returns:
            list[dict]: A list of search results.
        """
        
        topic = self._normalise_topic(topic)

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': f'Find information about: {topic}'}
        ]

        response = self._chat(messages)
        if response:
            reply = response['message']['content']
            tool_call = self._parse_tool_call(reply)

            if tool_call and tool_call['tool'] in ('web_search', 'tavily_search'):
                args = tool_call.get('args', {})
                query = args.get('query', topic)
                max_results = args.get('max_results', 8)

                try:
                    max_results = int(max_results)
                except (TypeError, ValueError):
                    max_results = 8

                provider = 'tavily' if tool_call['tool'] == 'tavily_search' else 'auto'
                print(f' [SearchAgent] Calling {tool_call["tool"]}("{query}")')
                results = web_search(query, max_results=max_results, provider=provider)
                if results:
                    return results
                print(' [SearchAgent] Tool call returned no results. Falling back to direct search.')

        print(f' [SearchAgent] Fallback direct search for: {topic}')
        return web_search(topic, max_results=8)