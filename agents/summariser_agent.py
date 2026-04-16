from agents.base_agent import BaseAgent
from tools.summariser import summarise_text

class SummariserAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name='SummariserAgent',
            system_prompt=(
                'You are a research summarisation expert. '
                'Condense the provided text into clear, concise bullet points.'
            ),
            tools=[]
        )

    def run(self, text: str) -> str:
        """Return a bullet-point summary of text."""
        # Step 1: extract key sentences with the tool
        extracted = summarise_text(text)

        # Step 2: ask the LLM to rewrite as clean bullets
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': f'Summarise this into 3-5 bullet points:\n\n{extracted}'}
        ]
        
        response = self._chat(messages)
        return response['message']['content']