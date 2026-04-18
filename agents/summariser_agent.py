from agents.base_agent import BaseAgent
from tools.summariser import summarise_text

class SummariserAgent(BaseAgent):
    """
    A specialized agent for creating concise summaries of research text.

    Args:
        BaseAgent (_type_): The base agent class that provides core functionalities like chat integration.
    """    
    
    def __init__(self) -> None:
        """
        Initialize the SummariserAgent with a specific system prompt that guides it to produce concise bullet-point summaries.
        The agent is designed to extract key facts without including long explanations or source descriptions, ensuring the output is focused and actionable.
        """        
        
        super().__init__(
            name='SummariserAgent',
            system_prompt=(
                'You are a research summarisation expert. '
                'Return only concise bullet points with key facts from the provided text. '
                'Do not include long explanations or copy large passages verbatim. '
                'Never include preamble lines, and never describe the sources themselves '
                '(for example, avoid phrases like "this biography says" or "another source states").'
            ),
            tools=[]
        )

    def run(self, text: str) -> str:
        """
        Generate a concise summary of the provided research text, focusing on key facts and avoiding lengthy explanations or source descriptions.

        Args:
            self (SummariserAgent): The instance of the SummariserAgent class.
            text (str): The research text to be summarised.

        Returns:
            str: The concise summary of the research text.
        """        
        
        chat_fn = self._chat
        summary = summarise_text(
            text=text,
            chat=chat_fn,
            max_sentences=4,
            system_prompt=self.system_prompt,
        )
        if not summary.strip():
            return '- No useful content was available to summarise.'

        return summary