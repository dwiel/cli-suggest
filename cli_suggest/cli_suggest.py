import os
import sys
import subprocess
import anthropic
import json
import argparse
import tempfile
import re
from typing import List, Tuple, Dict
from ratelimit import limits, sleep_and_retry
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from collections import Counter
from textwrap import dedent
from prettytable import PrettyTable
import requests
from bs4 import BeautifulSoup
import html2text

API_KEY = None
RATE_LIMIT = 20  # requests per minute
PERPLEXITY_API_KEY = None


def load_api_keys() -> None:
    global API_KEY, PERPLEXITY_API_KEY
    config_file = os.path.expanduser("~/.config/scratch/config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
            API_KEY = config.get("CLAUDE_API_KEY")
            PERPLEXITY_API_KEY = config.get("PERPLEXITY_API_KEY")
    if not API_KEY:
        print("Error: Claude API key not found in config file.")
        print(f"Please ensure you have a valid 'CLAUDE_API_KEY' in {config_file}")
        print("You can obtain an API key from https://www.anthropic.com")
        sys.exit(1)
    if not PERPLEXITY_API_KEY:
        print("Warning: Perplexity API key not found in config file.")
        print(f"Please add a valid 'PERPLEXITY_API_KEY' to {config_file} to use the /perplexity command")
        print("You can obtain an API key from https://www.perplexity.ai")


@sleep_and_retry
@limits(calls=RATE_LIMIT, period=60)
def rate_limited_api_call(client, prompt, max_tokens=100):
    return client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=max_tokens,
        temperature=0,
        system="You are a command-line suggestion assistant. Provide concise, accurate command-line suggestions.",
        messages=[{"role": "user", "content": prompt}],
    )


def get_recent_commands(limit=10):
    """Get the most recent commands from atuin history"""
    try:
        result = subprocess.run(
            ["atuin", "history", "list", "--cmd-only", "--limit", str(limit)],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().split("\n")
    except Exception as e:
        print(f"Error fetching recent commands: {e}")
        return []


def get_most_common_commands(limit=50):
    """Get the most common commands using atuin stats"""
    try:
        result = subprocess.run(
            ["atuin", "stats", "--count", str(limit)], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error: atuin stats command failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return []

        lines = result.stdout.strip().split("\n")
        if not lines:
            print("Warning: atuin stats returned no output")
            return []

        commands = []
        for line in lines:
            # Skip the last two lines which contain totals
            if line.startswith("Total commands:") or line.startswith(
                "Unique commands:"
            ):
                continue
            # Use regex to extract the command
            line = line[line.find("]") + 1:].strip()
            # remove any unicode or color codes
            line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            match = re.match(r"\s*(\d+)\s+(.*)", line)
            if match:
                count, cmd = match.groups()
                commands.append(cmd.strip())
            else:
                print(f"Warning: Unexpected line format: {line}")

        if not commands:
            print("Warning: No commands extracted from atuin stats output")
            print(f"Raw output: {result.stdout}")

        return commands
    except Exception as e:
        print(f"Error fetching common commands: {e}")
        return []


def get_global_context() -> Dict[str, str]:
    """Gather global context information"""
    context = {
        "OS": os.name,
        "PWD": os.getcwd(),
        "Recent_Commands": ", ".join(get_recent_commands()),
        "Common_Commands": ", ".join(get_most_common_commands()),
    }
    return context


def add_file_to_context(filename: str) -> str:
    """Read file contents and return them as a string"""
    try:
        with open(filename, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except Exception as e:
        return f"Error reading file '{filename}': {str(e)}"


def get_suggestion(
    query: str,
    conversation_history: str,
    global_context: Dict[str, str],
    is_multiline: bool = False,
) -> str:
    """Use Claude to suggest a command or script based on the query, conversation history, and global context"""
    client = anthropic.Anthropic(api_key=API_KEY)

    context_str = "\n".join([f"{k}: {v}" for k, v in global_context.items()])

    if is_multiline:
        prompt = f"""Suggest a multiline bash script for the following request, taking into account the conversation history and global context:

Global context:
{context_str}

Conversation history:
{conversation_history}

Current request: {query}

Provide only the bash script, without any explanation:"""
    else:
        prompt = f"""Suggest a concise command-line instruction for the following request, taking into account the conversation history and global context:

Global context:
{context_str}

Conversation history:
{conversation_history}

Current request: {query}

Provide only the command, without any explanation:"""

    message = rate_limited_api_call(
        client, prompt, max_tokens=300 if is_multiline else 100
    )
    return message.content[0].text.strip()


def ask_question(query, conversation_history, global_context: Dict[str, str]):
    """Use Claude to answer a question based on the query, conversation history, and global context"""
    client = anthropic.Anthropic(api_key=API_KEY)

    context_str = "\n".join([f"{k}: {v}" for k, v in global_context.items()])

    prompt = f"""Answer the following question, taking into account the conversation history and global context:

Global context:
{context_str}

Conversation history:
{conversation_history}

Current question: {query}

Provide a concise and informative answer:"""

    message = rate_limited_api_call(client, prompt, max_tokens=300)
    return message.content[0].text.strip()


def extract_code_from_backticks(text: str) -> str:
    """Extract code from triple backticks if present."""
    import re

    match = re.search(r"```(?:\w+)?\n([\s\S]*?)\n```", text)
    if match:
        extracted_code = match.group(1).strip()
        return extracted_code
    return text


def execute_command(suggested_command, is_multiline=False):
    try:
        suggested_command = extract_code_from_backticks(suggested_command)

        if is_multiline:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sh", delete=False
            ) as temp_script:
                temp_script.write(suggested_command)
                temp_script_path = temp_script.name

            # Execute the script, streaming stdout to console and capturing it
            process = subprocess.Popen(
                f"bash {temp_script_path}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        else:
            # Add the command to atuin history
            escaped_command = suggested_command.replace("'", "'\\''")
            atuin_start = subprocess.run(
                f"atuin history start -- '{escaped_command}'",
                shell=True,
                check=True,
                capture_output=True,
                text=True,
            )
            atuin_id = atuin_start.stdout.strip()

            # Execute the command, streaming stdout to console and capturing it
            process = subprocess.Popen(
                suggested_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        captured_output = []
        for line in process.stdout:
            print(line, end="")  # Stream to console
            captured_output.append(line)  # Capture for history

        exit_code = process.wait()

        if not is_multiline:
            subprocess.run(
                f"atuin history end --exit {exit_code} {atuin_id}",
                shell=True,
                check=True,
            )

        if is_multiline:
            os.unlink(temp_script_path)

        return "".join(captured_output)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return str(e)


def execute_shell_command(command):
    """Execute a shell command directly, print its output in real-time, and return the full output"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = []
        for line in process.stdout:
            print(line, end="")  # Print output in real-time
            output.append(line)
        process.wait()
        return "".join(output)
    except subprocess.CalledProcessError as e:
        error_message = f"Error: {e.stderr}"
        print(error_message)
        return error_message


def copy_context_to_clipboard(conversation_history):
    """Copy the current global context and conversation history to the Mac clipboard"""
    context = get_global_context()
    context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
    
    full_content = f"""Global Context:
{context_str}

Conversation History:
{conversation_history}"""

    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(full_content.encode("utf-8"))
        print("Global context and conversation history copied to clipboard.")
    except Exception as e:
        print(f"Error copying to clipboard: {e}")


def webpage_to_markdown(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        
        h = html2text.HTML2Text()
        h.ignore_links = False
        markdown = h.handle(text)
        
        return markdown
    except Exception as e:
        print(f"Error converting webpage to markdown: {e}")
        return None


def perplexity_query(query: str, conversation_history: List[str], global_context: Dict[str, str]) -> str:
    """Use Perplexity API to get an answer for the given query, including context and conversation history"""
    if not PERPLEXITY_API_KEY:
        return "Error: Perplexity API key not set. Please add it to your config file."

    url = "https://api.perplexity.ai/chat/completions"
    
    context_str = "\n".join([f"{k}: {v}" for k, v in global_context.items()])
    history_str = "\n".join(conversation_history)
    
    full_query = f"""Global Context:
{context_str}

Conversation History:
{history_str}

Current Query: {query}

Please provide a concise and accurate answer based on the above context and query."""

    payload = {
        "model": "llama-3.1-sonar-huge-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide concise and accurate answers based on the given context and conversation history."
            },
            {
                "role": "user",
                "content": full_query
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": False
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"Error querying Perplexity API: {str(e)}"


def process_suggestion(query, conversation_history):
    global_context = get_global_context()

    if query.startswith("!"):
        command = query[1:].strip()
        print(f"> {command}")
        captured_output = execute_shell_command(command)
        return command, captured_output, conversation_history
    elif query.startswith("/ask "):
        question = query[5:].strip()
        answer = ask_question(question, "\n".join(conversation_history), global_context)
        print(f"Answer: {answer}")
        return f"/ask {question}", answer, conversation_history
    elif query.startswith("/sh "):
        command = query[4:].strip()
        print(f"> {command}")
        captured_output = execute_command(command)
        return command, captured_output, conversation_history
    elif query.startswith("/multi "):
        script_request = query[7:].strip()
        suggested_script = get_suggestion(
            script_request, "\n".join(conversation_history), global_context, is_multiline=True
        )
        print(f"Suggested script:\n{suggested_script}")
        
        # Add the suggested script to the conversation history
        conversation_history.append(f"Assistant (multi-line script suggestion):\n{suggested_script}")

        while True:
            choice = input("\nRun this script? [Y]es/[N]o/[E]dit: ").lower()
            if choice in ["y", "yes", ""]:
                captured_output = execute_command(suggested_script, is_multiline=True)
                return f"/multi {script_request}", captured_output, conversation_history
            elif choice in ["n", "no"]:
                return f"/multi {script_request}", "[Script not executed]", conversation_history
            elif choice in ["e", "edit"]:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".sh", delete=False
                ) as temp_script:
                    temp_script.write(suggested_script)
                    temp_script_path = temp_script.name

                subprocess.run(["vi", temp_script_path])

                with open(temp_script_path, "r") as temp_script:
                    suggested_script = temp_script.read()

                os.unlink(temp_script_path)
                print(f"Updated script:\n{suggested_script}")
                
                # Add the updated script to the conversation history
                conversation_history.append(f"User edited script:\n{suggested_script}")
            else:
                print("Invalid choice. Please enter Y, N, or E.")
    elif query.strip().lower() == "/copy":
        copy_context_to_clipboard("\n".join(conversation_history))
        return "/copy", "Global context and conversation history copied to clipboard", conversation_history
    elif query.strip().lower() == "/context":
        show_global_context()
        return "/context", "Global context displayed", conversation_history
    elif query.startswith("/add "):
        filename = query[5:].strip()
        file_contents = add_file_to_context(filename)
        if file_contents.startswith("Error:"):
            print(file_contents)
            return f"/add {filename}", file_contents, conversation_history
        else:
            global_context[f"File_{filename}"] = file_contents
            print(f"Added contents of '{filename}' to the context.")
            return f"/add {filename}", f"Contents of '{filename}' added to context", conversation_history
    elif query.startswith("/web "):
        url = query[5:].strip()
        markdown = webpage_to_markdown(url)
        if markdown:
            global_context[f"Webpage_{url}"] = markdown[:1000]  # Limit to first 1000 characters
            print(f"Added content of '{url}' to the context (first 1000 characters).")
            return f"/web {url}", f"Content of '{url}' added to context", conversation_history
        else:
            return f"/web {url}", f"Error: Failed to fetch or convert '{url}'", conversation_history
    elif query.startswith("/perplexity ") or query.startswith("/perp "):
        perplexity_query_text = query[11:].strip() if query.startswith("/perplexity ") else query[6:].strip()
        answer = perplexity_query(perplexity_query_text, conversation_history, global_context)
        print(f"Perplexity Answer: {answer}")
        return f"/perplexity {perplexity_query_text}", answer, conversation_history
    else:
        suggested_command = get_suggestion(query, "\n".join(conversation_history), global_context)
        print(f"> {suggested_command}")

        run_choice = input("\nRun? [Y/n]: ").lower()
        if run_choice in ["y", ""]:
            captured_output = execute_command(suggested_command)
            return suggested_command, captured_output, conversation_history
        else:
            return suggested_command, "[Command not executed]", conversation_history


def handle_conversation():
    conversation_history = []
    history_file = os.path.expanduser("~/.cli_suggest_history")
    session = PromptSession(history=FileHistory(history_file))

    print("Welcome to CLI Suggest. Available commands:")
    print_help_table()
    print("Enter your request or type '/help' to see the command list again.")

    while True:
        try:
            query = session.prompt("> ")
        except EOFError:
            break

        if query.lower() == "exit":
            break
        elif query.lower() == "/help":
            print_help_table()
            continue

        conversation_history.append(f"User: {query}")
        suggested_command, output, updated_history = process_suggestion(
            query, conversation_history
        )

        conversation_history = updated_history

        if query.startswith("!"):
            conversation_history.append(f"User executed: {suggested_command}")
        else:
            conversation_history.append(f"Assistant: {suggested_command}")

        if output:
            conversation_history.append(f"Output: {output}")

        if output == "[Command not executed]":
            conversation_history.append("User: [Chose not to execute the command]")


def show_global_context():
    """Display the current global context"""
    context = get_global_context()
    context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
    print("\nCurrent Global Context:")
    print(context_str)


def print_help_table():
    table = PrettyTable()
    table.field_names = ["Command", "Description"]
    table.align["Command"] = "l"
    table.align["Description"] = "l"
    table.max_width["Description"] = 60
    table.add_rows([
        ["<query>", "Get a command suggestion based on your query"],
        ["!<command>", "Execute a direct bash command"],
        ["/multi <query>", "Get a suggestion for a multiline script"],
        ["/ask <question>", "Ask a question about command-line operations"],
        ["/sh <command>", "Execute a specific shell command"],
        ["/context", "Display the current global context"],
        ["/copy", "Copy global context and conversation history to clipboard"],
        ["/add <filename>", "Add file contents to the context"],
        ["/web <url>", "Add webpage content as markdown to the context"],
        ["/perplexity <query>", "Get an answer using the Perplexity API"],
        ["/perp <query>", "Alias for /perplexity"],
        ["/help", "Show this help table"],
        ["exit", "Quit the program"]
    ])
    print("\nAvailable commands:")
    print(table)


import base64

def handle_failed_command(failed_command: str) -> None:
    """Handle a failed command and suggest a fix"""
    client = anthropic.Anthropic(api_key=API_KEY)

    prompt = f"""A command has failed. Suggest a fix or alternative command.

Failed command: {failed_command}

Provide only a single command to fix the issue or an alternative command, without any explanation:"""

    message = rate_limited_api_call(client, prompt, max_tokens=200)
    suggested_command = message.content[0].text.strip()

    print(f"Suggested fix: {suggested_command}")
    
    run_choice = input("\nRun this command? [Y/n]: ").lower()
    if run_choice in ["y", ""]:
        captured_output = execute_command(suggested_command)
        print(captured_output)
    else:
        print("Command not executed.")

def main():
    parser = argparse.ArgumentParser(description="Get command-line suggestions.")
    parser.add_argument("--hook", action="store_true", help="Run in hook mode for failed commands")
    parser.add_argument("--failed-command", help="The failed command")
    parser.add_argument(
        "query", nargs=argparse.REMAINDER, help="The query for command suggestion"
    )
    args = parser.parse_args()

    load_api_keys()

    if args.hook:
        if not args.failed_command:
            print("Error: --failed-command is required in hook mode")
            sys.exit(1)
        handle_failed_command(args.failed_command)
    elif args.query:
        query = " ".join(args.query)
        process_suggestion(query, "")
    else:
        handle_conversation()

if __name__ == "__main__":
    main()
