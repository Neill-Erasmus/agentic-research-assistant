import json
import re

from agents.base_agent import BaseAgent
from agents.search_agent import SearchAgent
from agents.summariser_agent import SummariserAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.citation_agent import CitationAgent

class ResearchOrchestrator:
    DEFAULT_AGENT_PLAN = ['SearchAgent', 'SummariserAgent', 'FactCheckerAgent', 'CitationAgent']

    def __init__(self):
        print('Initialising agents...')
        self.search_agent = SearchAgent()
        self.summariser_agent = SummariserAgent()
        self.fact_checker_agent = FactCheckerAgent()
        self.citation_agent = CitationAgent()
        self.planner_agent = BaseAgent(
            name='PlannerAgent',
            system_prompt='You are an orchestration planner for a multi-agent research assistant.',
            tools=[]
        )
        print('All agents ready.\n')

    def run(self, query: str) -> str:
        print(f'Orchestrator received query: "{query}"\n')

        plan = self._plan_agents(query)
        print(f' Planned agent sequence: {", ".join(plan)}\n')

        results: list[dict] = []
        summary = '- Not requested by orchestration plan.'
        fact_check = '- Not requested by orchestration plan.'
        citations = ['Not requested by orchestration plan.']

        for step_idx, agent_name in enumerate(plan, 1):
            print(f'[Step {step_idx}] Dispatching {agent_name}...')

            if agent_name == 'SearchAgent':
                try:
                    results = self.search_agent.run(query)
                except Exception as exc:
                    return f'Research pipeline failed during search: {exc}'

                if results:
                    print(f' Found {len(results)} results.\n')
                else:
                    print(' No results found.\n')
                continue

            if agent_name == 'SummariserAgent':
                combined_text = self._build_summary_input(results)
                if not combined_text.strip():
                    summary = '- No search results available for summarisation.'
                    print(' Summariser skipped due to missing search results.\n')
                    continue

                try:
                    summary = self.summariser_agent.run(combined_text)
                except Exception as exc:
                    summary = f'- Summary generation failed: {exc}'
                print(' Summary complete.\n')
                continue

            if agent_name == 'FactCheckerAgent':
                if not summary.strip() or summary.startswith('- Not requested'):
                    fact_check = '- No summary available for fact-checking.'
                    print(' FactChecker skipped due to missing summary.\n')
                    continue

                try:
                    fact_check = self.fact_checker_agent.run(summary)
                except Exception as exc:
                    fact_check = f'- Fact-check generation failed: {exc}'
                print(' Fact-check complete.\n')
                continue

            if agent_name == 'CitationAgent':
                if not results:
                    citations = ['No search results available for citation formatting.']
                    print(' CitationAgent skipped due to missing search results.\n')
                    continue

                try:
                    citations = self.citation_agent.run(results)
                except Exception as exc:
                    citations = [f'Citation generation failed: {exc}']
                print(' Citations formatted.\n')

        report = self._compile_report(query, plan, summary, fact_check, citations)
        return report

    def _plan_agents(self, query: str) -> list[str]:
        plan_messages = [
            {
                'role': 'system',
                'content': (
                    'Choose which agents should run for the user query. '
                    'Return ONLY a JSON list of agent names in execution order.\n\n'
                    'Allowed agents:\n'
                    '- SearchAgent\n'
                    '- SummariserAgent\n'
                    '- FactCheckerAgent\n'
                    '- CitationAgent\n\n'
                    'Rules:\n'
                    '- Output must be valid JSON only (no prose, no markdown).\n'
                    '- Use each agent at most once.\n'
                    '- If the query needs external info, include SearchAgent before downstream agents.\n'
                    '- SummariserAgent depends on search output.\n'
                    '- FactCheckerAgent depends on summary output.\n'
                    '- CitationAgent depends on search output.'
                ),
            },
            {'role': 'user', 'content': f'Query: {query}'},
        ]

        response = self.planner_agent._chat(plan_messages)
        response_text = self._extract_chat_content(response)
        parsed_plan = self._parse_agent_plan(response_text)

        if parsed_plan:
            return parsed_plan

        print(' [PlannerAgent] Invalid or empty plan. Falling back to default pipeline.')
        return self.DEFAULT_AGENT_PLAN.copy()

    def _extract_chat_content(self, response: dict | None) -> str:
        if not response or not isinstance(response, dict):
            return ''
        return str(response.get('message', {}).get('content', '')).strip()

    def _parse_agent_plan(self, text: str) -> list[str]:
        if not text:
            return []

        candidates: list[str] = [text.strip()]

        fenced_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text, flags=re.IGNORECASE)
        candidates.extend(block.strip() for block in fenced_blocks if block.strip())

        bracketed = re.search(r'\[[\s\S]*\]', text)
        if bracketed:
            candidates.append(bracketed.group(0).strip())

        for candidate in candidates:
            parsed = self._parse_agent_plan_json(candidate)
            if parsed:
                return parsed

        return []

    def _parse_agent_plan_json(self, payload: str) -> list[str]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        if isinstance(data, dict):
            data = data.get('agents', [])

        if not isinstance(data, list):
            return []

        selected: list[str] = []
        seen: set[str] = set()
        for name in data:
            canonical = self._canonical_agent_name(name)
            if not canonical or canonical in seen:
                continue
            selected.append(canonical)
            seen.add(canonical)

        return selected

    def _canonical_agent_name(self, name: object) -> str | None:
        if not isinstance(name, str):
            return None

        token = re.sub(r'[^a-z]', '', name.lower())
        alias_map = {
            'search': 'SearchAgent',
            'searchagent': 'SearchAgent',
            'summariser': 'SummariserAgent',
            'summarize': 'SummariserAgent',
            'summarizer': 'SummariserAgent',
            'summariseragent': 'SummariserAgent',
            'summarizeragent': 'SummariserAgent',
            'factcheck': 'FactCheckerAgent',
            'factchecker': 'FactCheckerAgent',
            'factcheckeragent': 'FactCheckerAgent',
            'citation': 'CitationAgent',
            'cite': 'CitationAgent',
            'citationagent': 'CitationAgent',
        }
        return alias_map.get(token)

    def _build_summary_input(self, results: list[dict]) -> str:
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
        return combined_text

    def _compile_report(self, query, plan, summary, fact_check, citations):
        lines = [
            f'RESEARCH REPORT',
            f'Query: {query}',
            f'=' * 50,
            '',
            'AGENT PLAN',
            '-' * 30,
            ', '.join(plan),
            '',
            'SUMMARY',
            '-' * 30,
            summary,
            '',
            'FACT CHECK',
            '-' * 30,
            fact_check,
            '',
            'SOURCES',
            '-' * 30,
        ]
        for i, c in enumerate(citations, 1):
            lines.append(f'[{i}] {c}')
        return '\n'.join(lines)