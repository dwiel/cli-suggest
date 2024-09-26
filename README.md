# CLI Suggest

CLI Suggest is an intelligent command-line tool that provides suggestions and assistance for command-line operations using Claude AI.

## Features

- Suggests commands based on user queries
- Provides multi-line script suggestions
- Answers questions about command-line operations
- Executes suggested commands with user confirmation
- Incorporates global context, including recent and common commands
- Displays current global context on demand
- Adds file contents to the context for improved suggestions
- Adds webpage content as markdown to the context

## TODO

- [x] Add global context to every command:
    - [x] OS, pwd
    - [x] Summary of recent commands run from the terminal
    - [x] List of top 20 most common commands
- [x] Add some way to show the current global context
- [ ] Implement auto tool selection (single line vs multi line vs ssh)
- [ ] Add command to copy the current context into mac clipboard
- [ ] Experiment with advanced capabilities based on auto tool selection
- [x] Implement more advanced statistics using atuin's capabilities (e.g., command chains, time-based stats)
- [ ] Somehow tell it that it has access to:
    - [ ] a kubernetes cluster
    - [ ] quite a few nodes via ssh
    - [ ] ? issues from sentry
    - [ ] ? notion db
    - [ ] ? codebase
    this really only matters if it can use tools and then continue to other steps

## Usage

Enter your request at the prompt. The following commands are available:

| Command | Description |
|---------|-------------|
| `<query>` | Get a command suggestion based on your query |
| `!<command>` | Execute a direct bash command |
| `/multi <query>` | Get a suggestion for a multiline script |
| `/ask <question>` | Ask a question about command-line operations |
| `/sh <command>` | Execute a specific shell command |
| `/context` | Display the current global context |
| `/copy` | Copy global context and conversation history to clipboard |
| `/add <filename>` | Add file contents to the context |
| `/web <url>` | Add webpage content as markdown to the context |
| `/help` | Show the help table |
| `exit` | Quit the program |

## Installation

(Add installation instructions here)

## Configuration

Ensure you have a valid 'CLAUDE_API_KEY' in `~/.config/scratch/config.json`. You can obtain an API key from https://www.anthropic.com.

## Dependencies

- Python 3.x
- anthropic
- prompt_toolkit
- atuin (for command history management)
- requests
- beautifulsoup4
- html2text

Note: This tool relies on `atuin` for command history management. Make sure you have `atuin` installed and properly configured on your system.

## Contributing

(Add contribution guidelines here)

## License

(Add license information here)

## Aider notes for now:

> /ask is there a way to use a less detailed  map to then determine which parts of a more detailed map should be inclu
ded in the final query?

Warning: it's best to only add files that need changes to the chat.
https://aider.chat/docs/troubleshooting/edit-errors.html
That's an excellent suggestion for improving the repo map functionality. Currently, aider doesn't have a built-in feature that uses a two-stage mapping process as you've described. However, your idea is a smart approach to balancing breadth and depth in large repositories. Here's how such a system could theoretically work:

1. Initial Broad Map:
   - Create a high-level map of the entire repository with minimal detail.
   - This map would include all directories and files but with very little content from each file.

2. Relevance Scoring:
   - Use this broad map to score the relevance of different parts of the codebase to the current task or query.
   - This could involve techniques like keyword matching, file name relevance, or even a quick AI assessment.

3. Detailed Mapping:
   - Based on the relevance scores, allocate more tokens to the most relevant parts of the codebase.
   - Create a more detailed map of these high-scoring areas, including more content and context.

4. Final Query Composition:
   - Combine the high-level overview with the detailed information from relevant areas.
   - This would provide both broad context and specific details where they're most needed.

While this exact process isn't currently implemented in aider, you can approximate this approach manually:

1. Use `/map` with a low token count to get a broad overview.
2. Based on this overview, identify key areas of interest.
3. Manually `/add` the most relevant files or directories for a more detailed look.
4. Use `/map_refresh` to update the repo map with this new context.