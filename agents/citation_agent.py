from agents.base_agent import BaseAgent
from tools.citation import format_citation

class CitationAgent(BaseAgent):
    """
    A specialized agent for formatting citations in APA style.

    Args:
        BaseAgent (_type_): The base agent class that provides common functionality for all agents.
    """    
    
    def __init__(self) -> None:
        """
        Initialize the CitationAgent with a specific system prompt and no tools.
        The system prompt instructs the agent to format references accurately in APA style.
        """        
        
        super().__init__(
            name='CitationAgent',
            system_prompt=(
                'You are a citation formatting specialist. '
                'Format references accurately in APA style.'
            ),
            tools=[]
        )

    def run(self : CitationAgent, results: list[dict]) -> list[str]:
        """
        Format a list of search results into APA-style citations.

        Args:
            self (CitationAgent): The instance of the CitationAgent class.
            results (list[dict]): A list of search results, each containing information about a reference.

        Returns:
            list[str]: A list of formatted APA-style citations.
        """        
        
        citations = []
        for r in results:
            author = (
                r.get('author')
                or r.get('authors')
                or r.get('byline')
                or r.get('publisher')
                or r.get('source')
                or r.get('site_name')
            )
            citation = format_citation(
                url=r.get('url', ''),
                title=r.get('title', 'Untitled'),
                author=author,
            )
            citations.append(citation)
        return citations