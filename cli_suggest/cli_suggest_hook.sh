#!/usr/bin/env bash

# Prevent multiple sourcing
if [[ -n "$CLI_SUGGEST_HOOK_LOADED" ]]; then
    return
fi
CLI_SUGGEST_HOOK_LOADED=1

# Initialize variable to store the last command
cli_suggest_last_command=""

# Function to handle failed commands
cli_suggest_hook() {
    local last_command="$1"
    local last_command_exit_code="$2"

    echo "Command failed: $last_command (Exit Code: $last_command_exit_code)" >&2
    cli-suggest --hook --failed-command "$last_command"
}

# preexec function to store the command being executed
cli_suggest_preexec() {
    # Store the command that is about to be executed
    cli_suggest_last_command="$1"
}

# TRAPZERR function to capture failed commands
TRAPZERR() {
    local exit_code=$?
    # Use the command stored in preexec
    local last_command="$cli_suggest_last_command"

    # Proceed only if a command was actually executed
    if [[ -n "$last_command" ]]; then
        cli_suggest_hook "$last_command" "$exit_code"
    fi

    # Reset the stored command
    cli_suggest_last_command=""
}

# Set up the hooks for Zsh
if [[ -n "$ZSH_VERSION" ]]; then
    # Ensure the functions are added only once
    if [[ -z "${preexec_functions[(r)cli_suggest_preexec]}" ]]; then
        preexec_functions+=(cli_suggest_preexec)
    fi
fi

echo "CLI Suggest hook loaded successfully" >&2
