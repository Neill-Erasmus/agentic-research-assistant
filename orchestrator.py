from agents.search_agent import SearchAgent
from agents.summariser_agent import SummariserAgent
from agents.citation_agent import CitationAgent

class ResearchOrchestrator:
    def __init__(self):
        print('Initialising agents...')
        self.search_agent = SearchAgent()
        self.summariser_agent = SummariserAgent()
        self.citation_agent = CitationAgent()
        print('All agents ready.\n')

    def run(self, query: str) -> str:
        """
        Orchestrate the full research pipeline:
        1. Search -> 2. Summarise each result -> 3. Cite -> 4. Compile
        """
        print(f'Orchestrator received query: "{query}"\n')

        print('[Step 1] Dispatching SearchAgent...')
        try:
            results = self.search_agent.run(query)
        except Exception as exc:
            return f'Research pipeline failed during search: {exc}'

        if not results:
            return 'No results found. Try a different query or check your network connection.'
        print(f' Found {len(results)} results.\n')

        print('[Step 2] Dispatching SummariserAgent...')
        source_blocks = []
        for idx, result in enumerate(results, 1):
            snippet = (result.get('snippet') or '').strip()
            if not snippet:
                continue
            if snippet[-1] not in '.!?':
                snippet += '.'
            source_blocks.append(f'Source {idx}: {snippet}')

        combined_text = '\n\n'.join(source_blocks)
        if not combined_text.strip():
            combined_text = '\n'.join(r.get('title', '') for r in results)

        try:
            summary = self.summariser_agent.run(combined_text)
        except Exception as exc:
            summary = f'- Summary generation failed: {exc}'
        print(' Summary complete.\n')

        print('[Step 3] Dispatching CitationAgent...')
        try:
            citations = self.citation_agent.run(results)
        except Exception as exc:
            citations = [f'Citation generation failed: {exc}']
        print(' Citations formatted.\n')

        report = self._compile_report(query, summary, citations)
        return report

    def _compile_report(self, query, summary, citations):
        lines = [
            f'RESEARCH REPORT',
            f'Query: {query}',
            f'=' * 50,
            '',
            'SUMMARY',
            '-' * 30,
            summary,
            '',
            'SOURCES',
            '-' * 30,
        ]
        for i, c in enumerate(citations, 1):
            lines.append(f'[{i}] {c}')
        return '\n'.join(lines)