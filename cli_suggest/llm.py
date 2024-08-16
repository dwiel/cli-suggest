import sys
import os
import json
import anthropic
from ratelimit import limits, sleep_and_retry

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
        print("Error: API key not found in config file.", file=sys.stderr)
        print(f"Please ensure you have a valid 'CLAUDE_API_KEY' in {config_file}", file=sys.stderr)
        print("You can obtain an API key from https://www.anthropic.com", file=sys.stderr)
        sys.exit(1)

@sleep_and_retry
@limits(calls=RATE_LIMIT, period=60)
def stream_response(client, prompt):
    with client.messages.stream(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end='', flush=True)
        print()  # Print a newline at the end

def main():
    load_api_key()
    client = anthropic.Anthropic(api_key=API_KEY)
    
    # Read input from stdin
    prompt = sys.stdin.read().strip()
    
    if not prompt:
        print("Error: No input provided.", file=sys.stderr)
        sys.exit(1)
    
    try:
        stream_response(client, prompt)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
