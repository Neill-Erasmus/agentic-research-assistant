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
        extracted = summarise_text(text)
        if not extracted.strip():
            return '- No useful content was available to summarise.'

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': (
                'Rewrite these research notes into 3-5 concise bullet points. '
                'Prioritise factual claims and avoid speculation.\n\n'
                f'{extracted}'
            )}
        ]

        response = self._chat(messages)
        if response and response.get('message', {}).get('content', '').strip():
            return response['message']['content']

        return extracted