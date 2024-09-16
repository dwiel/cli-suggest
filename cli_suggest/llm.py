import argparse
import sys

from .anthropic_client import AnthropicClient

def main():
    parser = argparse.ArgumentParser(
        description="concatenates stdin and an optional prompt to an amazing LLM that can do all kinds of things and feeds the results to stdout"
    )
    parser.add_argument(
        "--prompt",
        help="Provide a prompt directly as an argument (optional)",
        nargs="?",
        const="",
    )
    args = parser.parse_args()

    anthropic_client = AnthropicClient()

    # Read input from stdin
    stdin_input = sys.stdin.read().strip()

    if args.prompt is not None:
        prompt = f"{args.prompt}\n{stdin_input}".strip()
    else:
        prompt = stdin_input

    try:
        anthropic_client.stream_response(prompt)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
