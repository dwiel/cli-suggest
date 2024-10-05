#!/usr/bin/env bash

# Prevent multiple sourcing
if [[ -n "$CLI_SUGGEST_HOOK_LOADED" ]]; then
    return
fi
CLI_SUGGEST_HOOK_LOADED=1

# Initialize variables to store the last command and its start time
cli_suggest_last_command=""
cli_suggest_command_start_time=0

# Function to handle failed commands
cli_suggest_hook() {
    local last_command="$1"
    local last_command_exit_code="$2"
    local execution_time="$3"

    echo "Command failed: $last_command (Exit Code: $last_command_exit_code, Execution Time: ${execution_time}s)" >&2
    
    # Check if the command starts with "pyton" or "python3"
    if [[ "$last_command" =~ ^(python|python3|pytest) ]]; then
        echo "Python command detected. Skipping suggestion." >&2
    else
        cli-suggest --hook --failed-command "$last_command"
    fi
}

# preexec function to store the command being executed and its start time
cli_suggest_preexec() {
    # Skip if we're in a completion context
    if [[ "$ZSH_EVAL_CONTEXT" == *:completion:* ]]; then
        return
    fi

    # Store the command that is about to be executed and its start time
    cli_suggest_last_command="$1"
    cli_suggest_command_start_time=$SECONDS
}

# TRAPZERR function to capture failed commands
TRAPZERR() {
    # Skip if we're in a completion context or shfunc:shfunc context
    if [[ "$ZSH_EVAL_CONTEXT" == *:completion:* ]] || [[ "$ZSH_EVAL_CONTEXT" == *shfunc:* ]]; then
        return
    fi

    local exit_code=$?
    # Use the command stored in preexec
    local last_command="$cli_suggest_last_command"

    # Calculate execution time
    local execution_time=$((SECONDS - cli_suggest_command_start_time))

    # Proceed only if a command was actually executed and it ran for less than 1 second
    if [[ -n "$last_command" && "$execution_time" -lt 1 ]]; then
        cli_suggest_hook "$last_command" "$exit_code" "$execution_time"
    fi

    # Reset the stored command and start time
    cli_suggest_last_command=""
    cli_suggest_command_start_time=0
}

# Set up the hooks for Zsh
if [[ -n "$ZSH_VERSION" ]]; then
    # Ensure the functions are added only once
    if [[ -z "${preexec_functions[(r)cli_suggest_preexec]}" ]]; then
        preexec_functions+=(cli_suggest_preexec)
    fi
fi

echo "CLI Suggest hook loaded successfully" >&2
