from agents.base_agent import BaseAgent
from tools.fact_checker import fact_check_summary

class FactCheckerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name='FactCheckerAgent',
            system_prompt=(
                'You are a research fact-checking specialist. '
                'Review summaries and identify likely false claims or unsupported statements.'
            ),
            tools=[]
        )

    def run(self, summary: str) -> str:
        """Return a bullet list of potential factual concerns in the summary."""
        concerns = fact_check_summary(
            summary=summary,
            chat=self._chat,
            system_prompt=self.system_prompt,
        )
        if not concerns.strip():
            return '- No fact-check concerns were generated.'

        return concerns