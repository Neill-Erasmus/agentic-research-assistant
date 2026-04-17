from agents.base_agent import BaseAgent
from tools.summariser import summarise_text

class SummariserAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name='SummariserAgent',
            system_prompt=(
                'You are a research summarisation expert. '
                'Return only concise bullet points with key facts from the provided text. '
                'Do not include long explanations or copy large passages verbatim.'
            ),
            tools=[]
        )

    def run(self, text: str) -> str:
        """Return a bullet-point summary of text using the BaseAgent Ollama chat client."""
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