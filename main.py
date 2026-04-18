from orchestrator import ResearchOrchestrator

def main() -> None:
    """
    Main function to run the Research Assistant application.
    It initializes the ResearchOrchestrator, prompts the user for research topics, and displays the generated reports.
    """    
    
    orchestrator = ResearchOrchestrator()

    print('=== Research Assistant ===')
    print('Type a research topic and press Enter.')
    print('Type "quit" to exit.\n')

    while True:
        query = input('Research topic: ').strip()

        if query.lower() in ('quit', 'exit', 'q'):
            print('Goodbye!')
            break

        if not query:
            continue

        try:
            report = orchestrator.run(query)
        except Exception as exc:
            report = f'Unexpected runtime error: {exc}'

        print('\n' + '=' * 50)
        print(report)
        print('=' * 50 + '\n')

if __name__ == '__main__':
    main()