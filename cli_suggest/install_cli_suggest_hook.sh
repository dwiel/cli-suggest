#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOK_SCRIPT="$SCRIPT_DIR/cli_suggest_hook.sh"
if [ ! -f "$HOOK_SCRIPT" ]; then
    HOOK_SCRIPT="$SCRIPT_DIR/../cli_suggest/cli_suggest_hook.sh"
fi
DEST_DIR="$HOME/.cli_suggest"
DEST_SCRIPT="$DEST_DIR/cli_suggest_hook.sh"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Copy the hook script to the destination directory
cp "$HOOK_SCRIPT" "$DEST_SCRIPT"

# Make the script executable
chmod +x "$DEST_SCRIPT"

# Function to add hook to shell config file
add_hook_to_config() {
    local config_file="$1"
    local hook_code="
# CLI Suggest Hook
if [ -f ~/.cli_suggest/cli_suggest_hook.sh ]; then
    source ~/.cli_suggest/cli_suggest_hook.sh
fi
"
    
    if ! grep -q "CLI Suggest Hook" "$config_file"; then
        echo "$hook_code" >> "$config_file"
        echo "Hook added to $config_file"
    else
        echo "Hook already present in $config_file"
    fi
}

# Add hook to .zshrc if it exists
if [ -f "$HOME/.zshrc" ]; then
    add_hook_to_config "$HOME/.zshrc"
fi

# Add hook to .bashrc if it exists
if [ -f "$HOME/.bashrc" ]; then
    add_hook_to_config "$HOME/.bashrc"
fi

echo "CLI Suggest hook installed successfully."
echo "Please restart your shell or run 'source ~/.zshrc' (for Zsh) or 'source ~/.bashrc' (for Bash) to activate the hook."
