from agents.base_agent import BaseAgent
from tools.fact_checker import fact_check_summary

class FactCheckerAgent(BaseAgent):
    """
    An agent that reviews summaries and identifies likely false claims or unsupported statements.

    Args:
        BaseAgent (_type_): The base agent class that provides common functionality for all agents, including the chat interface.
    """    
    
    def __init__(self):
        """
        Initialize the FactCheckerAgent with a specific system prompt that defines its role and behavior.
        The agent is designed to review summaries and identify potential factual concerns without providing explanations or justifications for its findings.
        """        
        
        super().__init__(
            name='FactCheckerAgent',
            system_prompt=(
                'You are a research fact-checking specialist. '
                'Review summaries and identify likely false claims or unsupported statements.'
            ),
            tools=[]
        )

    def run(self, summary: str) -> str:
        """
        Review a summary and identify potential factual concerns.

        Args:
            summary (str): The summary to be fact-checked.

        Returns:
            str: A list of potential factual concerns in the summary.
        """        
        
        concerns = fact_check_summary(
            summary=summary,
            chat=self._chat,
            system_prompt=self.system_prompt,
        )
        if not concerns.strip():
            return '- No fact-check concerns were generated.'

        return concerns