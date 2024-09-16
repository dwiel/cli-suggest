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

Note: This tool relies on `atuin` for command history management. Make sure you have `atuin` installed and properly configured on your system.

## Contributing

(Add contribution guidelines here)

## License

(Add license information here)
