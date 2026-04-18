import json
import re

from agents.base_agent import BaseAgent
from agents.search_agent import SearchAgent
from agents.summariser_agent import SummariserAgent
from agents.fact_checker_agent import FactCheckerAgent
from agents.citation_agent import CitationAgent

class ResearchOrchestrator:
    """
    Orchestrates the execution of multiple agents to fulfill a research query.
    The orchestrator manages the flow of information between agents, maintains session memory for follow-up queries, and compiles the final report.
    It uses a PlannerAgent to determine which agents to run based on the user's query and ensures that dependencies between agents are respected (e.g., if SearchAgent is used, CitationAgent must also be included). 
    """    
    
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

    def __init__(self) -> None:
        """
        Initialize the ResearchOrchestrator by instantiating all the necessary agents and setting up session memory.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class being initialized.
        """        
        
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

    def run(self, query : str) -> str:
        """
        Execute the research pipeline for a given query by determining the appropriate agents to run, managing their execution, and compiling the final report.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class executing the run method.
            query (str): The research query to be processed.

        Returns:
            str: The compiled research report.
        """        
        
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

    def _resolve_query_with_memory(self, query : str) -> tuple[str, list[dict]]:
        """
        Check if the query references a specific result from a previous search in the session memory.
        If so, extract that result and build an effective query based on its content.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            query (str): The research query to be processed.

        Returns:
            tuple[str, list[dict]]: A tuple containing the resolved query and the referenced result.
        """       
        
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

    def _extract_referenced_result_index(self, query : str) -> int | None:
        """
        Extract the index of a referenced search result from the query, if present.
        The method looks for ordinal indicators (e.g., "first result", "2nd source") to determine which result the user is referring to.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            query (str): The research query to be processed.

        Returns:
            int | None: The index of the referenced result, or None if not found.
        """        
        
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
        """
        Retrieve the most recent entry from session memory that contains search results.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.

        Returns:
            dict | None: The most recent entry containing search results, or None if not found.
        """        
        
        for entry in reversed(self.session_memory):
            if entry.get('results'):
                return entry
        return None

    def _build_query_from_result(self, original_query: str, result: dict) -> str:
        """
        Construct an effective query by extracting key information from a referenced search result.
        The method combines the title, snippet, and URL of the result to create a new query that can be used for follow-up research.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            original_query (str): The original research query.
            result (dict): The search result from which to extract information.

        Returns:
            str: The constructed query for follow-up research.
        """        
        
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
        query : str,
        effective_query : str,
        plan : list[str],
        results : list[dict],
        summary : str,
        fact_check : str,
        citations : list[str],
    ) -> None:
        """
        Store the details of a completed research run in session memory for potential reference in future follow-up queries.
        The stored information includes the original query, the effective query used for agent execution, the plan of agents that were run, the results obtained, the summary generated, the fact-checking output, and the formatted citations.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            query (str): The original research query.
            effective_query (str): The effective query used for agent execution.
            plan (list[str]): The plan of agents that were run.
            results (list[dict]): The search results obtained.
            summary (str): The summary generated.
            fact_check (str): The fact-checking output.
            citations (list[str]): The formatted citations.
        """        
        
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

    def _plan_agents(self, query : str) -> list[str]:
        """
        Determine which agents to run for a given query by consulting the PlannerAgent.
        The method constructs a prompt that describes the allowed agents and the rules for selecting them, then parses the PlannerAgent's response to extract a valid execution plan.
        If the PlannerAgent fails to provide a valid plan, a default sequence of agents is returned.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            query (str): The research query for which to determine agent execution.

        Returns:
            list[str]: A list of agent names in the order they should be executed.
        """      
        
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

    def _ensure_citation_if_search_used(self, plan : list[str]) -> list[str]:
        """
        Ensure that if SearchAgent is included in the plan, CitationAgent is also included and correctly ordered.
        This method checks the proposed agent plan for the presence of SearchAgent and enforces the inclusion of CitationAgent if necessary, as well as ensuring that CitationAgent runs after SearchAgent to satisfy the dependency.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            plan (list[str]): The proposed agent plan.

        Returns:
            list[str]: The revised agent plan with CitationAgent included if necessary.
        """        
        
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

    def _extract_chat_content(self, response : dict | None) -> str:
        """
        Extract the content of a chat response from an agent, handling potential issues with missing or malformed responses.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            response (dict | None): The chat response from the agent.

        Returns:
            str: The extracted content from the chat response.
        """        
        
        if not response or not isinstance(response, dict):
            return ''
        return str(response.get('message', {}).get('content', '')).strip()

    def _parse_agent_plan(self, text : str) -> list[str]:
        """
        Parse the agent plan from the PlannerAgent's response text by looking for JSON structures that contain a list of agent names.
        The method searches for fenced code blocks, bracketed sections, and the entire text as potential sources of the JSON plan, then validates and canonicalizes the agent names to produce a final execution plan.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            text (str): The text to parse for the agent plan.

        Returns:
            list[str]: The list of canonicalized agent names.
        """            
        
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

    def _parse_agent_plan_json(self, payload : str) -> list[str]:
        """
        Parse a JSON payload to extract a list of agent names.
        The method handles different potential structures of the JSON (either a direct list or a dictionary containing an 'agents' key) and canonicalizes the agent names to ensure they match the expected set of agents.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            payload (str): The JSON payload to parse.

        Returns:
            list[str]: The list of canonicalized agent names.
        """               
        
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

    def _canonical_agent_name(self, name : object) -> str | None:
        """
        Convert a given agent name to its canonical form if it matches known aliases, or return None if it does not correspond to a valid agent.
        The method normalizes the input name by removing non-alphabetic characters and converting to lowercase, then checks against a mapping of known aliases to canonical agent names.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            name (object): The agent name to canonicalize.

        Returns:
            str | None: The canonical agent name if it matches a known alias, otherwise None.
        """                
        
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

    def _build_summary_input(self, results : list[dict]) -> str:
        """
        Construct the input text for the SummariserAgent by combining snippets from search results.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            results (list[dict]): The list of search results.

        Returns:
            str: The combined input text for the SummariserAgent.
        """            
        
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

    def _compile_report(self, query : str, plan : list[str], summary : str, fact_check : str, citations : list[str]) -> str:
        """
        Compile the final research report by combining all the generated content.

        Args:
            self (ResearchOrchestrator): The instance of the ResearchOrchestrator class.
            query (str): The original research query.
            plan (list[str]): The list of agents in the execution plan.
            summary (str): The combined summary from the search results.
            fact_check (str): The fact-checking results.
            citations (list[str]): The list of cited sources.

        Returns:
            str: The complete research report.
        """            
        
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