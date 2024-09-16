import os
import json
import sys
import anthropic
from ratelimit import limits, sleep_and_retry

API_KEY = None
RATE_LIMIT = 20  # requests per minute

class AnthropicClient:
    def __init__(self):
        self.api_key = None
        self.client = None
        self.load_api_key()

    def load_api_key(self):
        config_file = os.path.expanduser("~/.config/scratch/config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
                self.api_key = config.get("CLAUDE_API_KEY")
        if not self.api_key:
            print("Error: API key not found in config file.", file=sys.stderr)
            print(
                f"Please ensure you have a valid 'CLAUDE_API_KEY' in {config_file}",
                file=sys.stderr,
            )
            print(
                "You can obtain an API key from https://www.anthropic.com", file=sys.stderr
            )
            sys.exit(1)
        self.client = anthropic.Anthropic(api_key=self.api_key)

    @sleep_and_retry
    @limits(calls=RATE_LIMIT, period=60)
    def stream_response(self, prompt):
        with self.client.messages.stream(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            print()  # Print a newline at the end

