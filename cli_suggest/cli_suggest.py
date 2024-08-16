import os
import sys
import subprocess
import anthropic
import json
import argparse
import tempfile
from ratelimit import limits, sleep_and_retry
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

API_KEY = None
RATE_LIMIT = 20  # requests per minute

def load_api_key():
    global API_KEY
    config_file = os.path.expanduser('~/.config/scratch/config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            API_KEY = config.get('CLAUDE_API_KEY')
    if not API_KEY:
        print("Error: API key not found in config file.")
        print(f"Please ensure you have a valid 'CLAUDE_API_KEY' in {config_file}")
        print("You can obtain an API key from https://www.anthropic.com")
        sys.exit(1)

@sleep_and_retry
@limits(calls=RATE_LIMIT, period=60)
def rate_limited_api_call(client, prompt, max_tokens=100):
    return client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=max_tokens,
        temperature=0,
        system="You are a command-line suggestion assistant. Provide concise, accurate command-line suggestions.",
        messages=[{"role": "user", "content": prompt}]
    )

def get_suggestion(query, conversation_history, is_multiline=False):
    """Use Claude to suggest a command or script based on the query and conversation history"""
    client = anthropic.Anthropic(api_key=API_KEY)
    
    if is_multiline:
        prompt = f"""Suggest a multiline bash script for the following request, taking into account the conversation history:

Conversation history:
{conversation_history}

Current request: {query}

Provide only the bash script, without any explanation:"""
    else:
        prompt = f"""Suggest a concise command-line instruction for the following request, taking into account the conversation history:

Conversation history:
{conversation_history}

Current request: {query}

Provide only the command, without any explanation:"""

    message = rate_limited_api_call(client, prompt, max_tokens=300 if is_multiline else 100)
    return message.content[0].text.strip()

def ask_question(query, conversation_history):
    """Use Claude to answer a question based on the query and conversation history"""
    client = anthropic.Anthropic(api_key=API_KEY)
    
    prompt = f"""Answer the following question, taking into account the conversation history:

Conversation history:
{conversation_history}

Current question: {query}

Provide a concise and informative answer:"""

    message = rate_limited_api_call(client, prompt, max_tokens=300)
    return message.content[0].text.strip()

def extract_code_from_backticks(text):
    """Extract code from triple backticks if present."""
    import re
    match = re.search(r'```(?:\w+)?\n([\s\S]*?)\n```', text)
    return match.group(1) if match else text

def execute_command(suggested_command, is_multiline=False):
    try:
        suggested_command = extract_code_from_backticks(suggested_command)
        
        if is_multiline:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_script:
                temp_script.write(suggested_command)
                temp_script_path = temp_script.name

            # Execute the script, streaming stdout to console and capturing it
            process = subprocess.Popen(f"bash {temp_script_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        else:
            # Add the command to atuin history
            escaped_command = suggested_command.replace("'", "'\\''")
            atuin_start = subprocess.run(f"atuin history start -- '{escaped_command}'", shell=True, check=True, capture_output=True, text=True)
            atuin_id = atuin_start.stdout.strip()

            # Execute the command, streaming stdout to console and capturing it
            process = subprocess.Popen(suggested_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        captured_output = []
        for line in process.stdout:
            print(line, end='')  # Stream to console
            captured_output.append(line)  # Capture for history

        exit_code = process.wait()

        if not is_multiline:
            subprocess.run(f"atuin history end --exit {exit_code} {atuin_id}", shell=True, check=True)

        if is_multiline:
            os.unlink(temp_script_path)

        return ''.join(captured_output)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return str(e)

def process_suggestion(query, conversation_history=""):
    if query.startswith("/ask "):
        question = query[5:].strip()
        answer = ask_question(question, conversation_history)
        print(f"Answer: {answer}")
        return f"/ask {question}", answer
    elif query.startswith("!"):
        command = query[1:].strip()
        print(f"> {command}")
        captured_output = execute_command(command)
        return command, captured_output
    elif query.startswith("/multi "):
        script_request = query[7:].strip()
        suggested_script = get_suggestion(script_request, conversation_history, is_multiline=True)
        print(f"Suggested script:\n{suggested_script}")
        
        run_choice = input("\nRun this script? [Y/n]: ").lower()
        if run_choice in ['y', '']:
            captured_output = execute_command(suggested_script, is_multiline=True)
            return f"/multi {script_request}", captured_output
        else:
            return f"/multi {script_request}", "[Script not executed]"
    else:
        suggested_command = get_suggestion(query, conversation_history)
        print(f"> {suggested_command}")
        
        run_choice = input("\nRun? [Y/n]: ").lower()
        if run_choice in ['y', '']:
            captured_output = execute_command(suggested_command)
            return suggested_command, captured_output
        else:
            return suggested_command, "[Command not executed]"

def handle_conversation():
    conversation_history = []
    history_file = os.path.expanduser('~/.cli_suggest_history')
    session = PromptSession(history=FileHistory(history_file))
    
    print("Enter your request, prefix with '!' for direct bash commands, '/multi' for multiline scripts, or type 'exit' to quit.")
    while True:
        try:
            query = session.prompt("> ")
        except EOFError:
            break
        if query.lower() == 'exit':
            break
        
        conversation_history.append(f"User: {query}")
        suggested_command, output = process_suggestion(query, "\n".join(conversation_history))
        
        if query.startswith("!"):
            conversation_history.append(f"User executed: {suggested_command}")
        else:
            conversation_history.append(f"Assistant: {suggested_command}")
        
        if output:
            conversation_history.append(f"Output: {output}")
        
        if output == "[Command not executed]":
            conversation_history.append("User: [Chose not to execute the command]")

def main():
    parser = argparse.ArgumentParser(description="Get command-line suggestions.")
    parser.add_argument("query", nargs=argparse.REMAINDER, help="The query for command suggestion")
    args = parser.parse_args()

    load_api_key()

    if args.query:
        query = " ".join(args.query)
        process_suggestion(query)
    else:
        handle_conversation()

if __name__ == "__main__":
    main()
