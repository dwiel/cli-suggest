#!/usr/bin/env bash

# Prevent multiple sourcing
if [[ -n "$CLI_SUGGEST_HOOK_LOADED" ]]; then
    return
fi
CLI_SUGGEST_HOOK_LOADED=1

# Initialize variables
cli_suggest_last_command=""
cli_suggest_last_exit_code=""

# Function to handle failed commands
cli_suggest_hook() {
    local last_command="$1"
    local last_command_exit_code="$2"

    if [[ $last_command_exit_code -ne 0 ]]; then
        echo "Command failed: $last_command" >&2
        cli-suggest --hook --failed-command "$last_command"
    fi
}

# Unique preexec function
cli_suggest_preexec() {
    # Store the command that is about to be executed
    cli_suggest_last_command="$1"
}

# Unique precmd function
cli_suggest_precmd() {
    # Proceed only if a command was actually executed
    if [[ -n "$cli_suggest_last_command" ]]; then
        local exit_code=$?
        if [[ $exit_code -ne 0 ]]; then
            cli_suggest_hook "$cli_suggest_last_command" "$exit_code"
        fi
        # Reset the stored command
        cli_suggest_last_command=""
    fi
}

# Set up the hook for Zsh
if [[ -n "$ZSH_VERSION" ]]; then
    # Ensure the functions are added only once
    if [[ -z "${precmd_functions[(r)cli_suggest_precmd]}" ]]; then
        precmd_functions+=(cli_suggest_precmd)
    fi
    if [[ -z "${preexec_functions[(r)cli_suggest_preexec]}" ]]; then
        preexec_functions+=(cli_suggest_preexec)
    fi
fi

echo "CLI Suggest hook loaded successfully" >&2
