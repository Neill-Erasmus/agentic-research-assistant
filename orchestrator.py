import json
import re

from agents.base_agent import BaseAgent
from agents.search_agent import SearchAgent
from agents.summariser_agent import SummariserAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.citation_agent import CitationAgent

class ResearchOrchestrator:
    DEFAULT_AGENT_PLAN = ['SearchAgent', 'SummariserAgent', 'FactCheckerAgent', 'CitationAgent']
    ORDINAL_RESULT_INDEX = {
        'first': 0,
        'second': 1,
        'third': 2,
        'fourth': 3,
        'fifth': 4,
        'sixth': 5,
        'seventh': 6,
        'eighth': 7,
        'ninth': 8,
        'tenth': 9,
    }

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
        self.session_memory: list[dict] = []
        print('All agents ready.\n')

    def run(self, query: str) -> str:
        print(f'Orchestrator received query: "{query}"\n')

        effective_query, seeded_results = self._resolve_query_with_memory(query)

        plan = self._plan_agents(effective_query)
        plan = self._ensure_citation_if_search_used(plan)
        print(f' Planned agent sequence: {", ".join(plan)}\n')

        results: list[dict] = [dict(item) for item in seeded_results]
        summary = '- Not requested by orchestration plan.'
        fact_check = '- Not requested by orchestration plan.'
        citations = ['Not requested by orchestration plan.']

        for step_idx, agent_name in enumerate(plan, 1):
            print(f'[Step {step_idx}] Dispatching {agent_name}...')

            if agent_name == 'SearchAgent':
                try:
                    results = self.search_agent.run(effective_query)
                except Exception as exc:
                    return f'Research pipeline failed during search: {exc}'

                if results:
                    print(f' Found {len(results)} results.\n')
                else:
                    if seeded_results:
                        results = [dict(item) for item in seeded_results]
                        print(' No fresh results found. Reusing referenced prior result from session memory.\n')
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

        self._remember_run(
            query=query,
            effective_query=effective_query,
            plan=plan,
            results=results,
            summary=summary,
            fact_check=fact_check,
            citations=citations,
        )

        report = self._compile_report(query, plan, summary, fact_check, citations)
        return report

    def _resolve_query_with_memory(self, query: str) -> tuple[str, list[dict]]:
        result_index = self._extract_referenced_result_index(query)
        if result_index is None:
            return query, []

        previous_entry = self._latest_memory_entry_with_results()
        if not previous_entry:
            print(' [Memory] Follow-up detected, but there are no prior results in this session yet.')
            return query, []

        previous_results = previous_entry.get('results') or []
        if result_index < 0 or result_index >= len(previous_results):
            print(
                f' [Memory] Follow-up asked for result {result_index + 1}, '
                f'but only {len(previous_results)} result(s) are available from the latest memory entry.'
            )
            return query, []

        selected_result = dict(previous_results[result_index])
        resolved_query = self._build_query_from_result(query, selected_result)
        source_query = previous_entry.get('query', 'previous query')
        title = (selected_result.get('title') or 'Untitled').strip()
        print(
            f' [Memory] Follow-up matched result {result_index + 1} '
            f'from "{source_query}": {title}.\n'
        )
        return resolved_query, [selected_result]

    def _extract_referenced_result_index(self, query: str) -> int | None:
        lowered = query.lower()

        numbered_patterns = (
            r'\b(?:result|source)\s*(?:number\s*)?#?\s*(\d+)(?:st|nd|rd|th)?\b',
            r'\b(\d+)(?:st|nd|rd|th)\s+(?:result|source)\b',
        )
        for pattern in numbered_patterns:
            match = re.search(pattern, lowered)
            if match:
                return max(0, int(match.group(1)) - 1)

        for word, index in self.ORDINAL_RESULT_INDEX.items():
            if re.search(rf'\b{word}\s+(?:result|source)\b', lowered):
                return index
            if re.search(rf'\b(?:result|source)\s+{word}\b', lowered):
                return index

        return None

    def _latest_memory_entry_with_results(self) -> dict | None:
        for entry in reversed(self.session_memory):
            if entry.get('results'):
                return entry
        return None

    def _build_query_from_result(self, original_query: str, result: dict) -> str:
        title = (result.get('title') or '').strip()
        snippet = (result.get('snippet') or '').strip()
        url = (result.get('url') or '').strip()

        query_parts = [title]
        if snippet:
            query_parts.append(snippet[:220])
        if url:
            query_parts.append(url)

        resolved_query = ' '.join(part for part in query_parts if part).strip()
        return resolved_query or original_query

    def _remember_run(
        self,
        query: str,
        effective_query: str,
        plan: list[str],
        results: list[dict],
        summary: str,
        fact_check: str,
        citations: list[str],
    ) -> None:
        memory_entry = {
            'query': query,
            'effective_query': effective_query,
            'plan': plan.copy(),
            'results': [dict(item) for item in results],
            'summary': summary,
            'fact_check': fact_check,
            'citations': list(citations),
        }
        self.session_memory.append(memory_entry)

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
                    '- If SearchAgent is included, CitationAgent must also be included.'
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

    def _ensure_citation_if_search_used(self, plan: list[str]) -> list[str]:
        if 'SearchAgent' not in plan:
            return plan

        if 'CitationAgent' not in plan:
            enforced_plan = plan + ['CitationAgent']
            print(' [Orchestrator] Enforcing CitationAgent because SearchAgent was selected.')
            return enforced_plan

        if plan.index('CitationAgent') < plan.index('SearchAgent'):
            reordered_plan = [agent for agent in plan if agent != 'CitationAgent']
            reordered_plan.append('CitationAgent')
            print(' [Orchestrator] Moving CitationAgent after SearchAgent to satisfy dependency.')
            return reordered_plan

        return plan

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