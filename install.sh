#!/bin/bash

# TIX Smart Installer - Simple and Reliable
# Version 8.0 - Final working solution with simple bash completion
# Usage: curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                TIX - Smart Installer v8.0                 ║"
echo "║          Lightning-fast Terminal Task Manager             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS and Architecture
OS=$(uname -s)
ARCH=$(uname -m)
echo -e "${YELLOW}📍 Detecting system...${NC}"
echo "   OS: $OS"
echo "   Architecture: $ARCH"

# Detect Shell
SHELL_NAME=$(basename "$SHELL")
echo "   Shell: $SHELL_NAME"
echo "   Bash Version: $BASH_VERSION"

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found. Please install Python 3.7+ first.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "   Python: $PYTHON_VERSION"

# Detect if we're in a virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}   Virtual Environment: Active${NC}"
    IN_VENV=true
else
    echo -e "${YELLOW}   Virtual Environment: Not active${NC}"
    IN_VENV=false
fi

# Function to install with pip
install_with_pip() {
    local pip_cmd="$1"
    local install_args="$2"

    if [ -f "setup.py" ] && [ -d "tix" ]; then
        echo "   Found local repository, installing in development mode..."
        $pip_cmd install -e . $install_args --quiet --upgrade || \
        $pip_cmd install -e . $install_args --quiet --upgrade --break-system-packages
    else
        echo "   Installing from GitHub..."
        $pip_cmd install $install_args --quiet --upgrade git+https://github.com/TheDevOpsBlueprint/tix-cli.git || \
        $pip_cmd install $install_args --quiet --upgrade --break-system-packages git+https://github.com/TheDevOpsBlueprint/tix-cli.git
    fi
}

# Install or upgrade TIX
echo -e "\n${YELLOW}📦 Installing TIX...${NC}"

# Check if pip/pip3 is available
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo -e "${YELLOW}📦 Installing pip...${NC}"
    curl -sSL https://bootstrap.pypa.io/get-pip.py | $PYTHON_CMD
    PIP_CMD="pip"
fi

# Handle installation based on environment
INSTALL_SUCCESS=false
INSTALL_METHOD=""

if [ "$IN_VENV" = true ]; then
    # In virtual environment - direct install
    echo "   Installing in virtual environment..."
    install_with_pip "$PIP_CMD" ""
    INSTALL_SUCCESS=true
    INSTALL_METHOD="venv"

elif [ "$OS" = "Darwin" ]; then
    # macOS with potential brew Python
    echo "   Detected macOS with managed Python environment..."

    # Try pipx (recommended for managed environments)
    if command -v pipx &> /dev/null; then
        echo "   Using pipx for isolated installation..."
        if [ -f "setup.py" ] && [ -d "tix" ]; then
            pipx install -e . --force
        else
            pipx install tix-cli --force || pipx install git+https://github.com/TheDevOpsBlueprint/tix-cli.git --force
        fi
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pipx"
    elif command -v brew &> /dev/null; then
        echo "   Installing pipx first..."
        brew install pipx
        pipx ensurepath
        export PATH="$HOME/.local/bin:$PATH"

        if [ -f "setup.py" ] && [ -d "tix" ]; then
            pipx install -e . --force
        else
            pipx install tix-cli --force || pipx install git+https://github.com/TheDevOpsBlueprint/tix-cli.git --force
        fi
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pipx"
    else
        echo "   Using pip with --user flag..."
        install_with_pip "$PIP_CMD" "--user"
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pip-user"
    fi

else
    # Linux or other OS
    echo "   Installing for $OS..."

    if install_with_pip "$PIP_CMD" "--user" 2>/dev/null; then
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pip-user"
    elif install_with_pip "$PIP_CMD" "" 2>/dev/null; then
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pip-system"
    else
        install_with_pip "$PIP_CMD" "--user --break-system-packages"
        INSTALL_SUCCESS=true
        INSTALL_METHOD="pip-user"
    fi
fi

# Ensure PATH includes ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"

# Verify tix is available
if ! command -v tix &> /dev/null; then
    echo -e "${RED}❌ Installation completed but 'tix' command not found.${NC}"
    echo -e "${YELLOW}Add this to your shell configuration:${NC}"
    echo -e "${GREEN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    exit 1
fi

echo -e "${GREEN}✅ TIX installed successfully!${NC}"

# Setup shell completion
echo -e "\n${YELLOW}🔧 Setting up shell completion...${NC}"

# Determine shell config file
case "$SHELL_NAME" in
    bash)
        CONFIG_FILE="$HOME/.bash_profile"
        [ "$OS" != "Darwin" ] && [ -f "$HOME/.bashrc" ] && CONFIG_FILE="$HOME/.bashrc"
        ;;
    zsh)
        CONFIG_FILE="$HOME/.zshrc"
        ;;
    fish)
        CONFIG_FILE="$HOME/.config/fish/config.fish"
        mkdir -p "$(dirname "$CONFIG_FILE")"
        ;;
    *)
        echo -e "${YELLOW}⚠️  Unknown shell: $SHELL_NAME${NC}"
        CONFIG_FILE=""
        ;;
esac

# Clean up any old TIX completion entries
if [ -f "$CONFIG_FILE" ] && [ "$SHELL_NAME" = "bash" ]; then
    # Create backup
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%s)" 2>/dev/null || true

    # Remove old TIX completion entries (using grep to avoid sed issues)
    grep -v "_tix_" "$CONFIG_FILE" > "$CONFIG_FILE.tmp" 2>/dev/null || true
    grep -v "TIX Completion" "$CONFIG_FILE.tmp" > "$CONFIG_FILE.tmp2" 2>/dev/null || true
    grep -v "TIX Command Completion" "$CONFIG_FILE.tmp2" > "$CONFIG_FILE.tmp3" 2>/dev/null || true
    mv "$CONFIG_FILE.tmp3" "$CONFIG_FILE" 2>/dev/null || true
    rm -f "$CONFIG_FILE.tmp" "$CONFIG_FILE.tmp2" 2>/dev/null || true
fi

# Add fresh completion
COMPLETION_ADDED=false

if [ "$SHELL_NAME" = "bash" ] && [ -n "$CONFIG_FILE" ]; then
    # Add PATH if needed
    if ! grep -q "export PATH.*\.local/bin" "$CONFIG_FILE" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CONFIG_FILE"
    fi

    # Add simple bash completion that works with Bash 3.2+
    cat >> "$CONFIG_FILE" << 'BASH_COMPLETION_EOF'

# TIX Completion - Simple version that works
_tix_simple() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local commands="add ls done rm clear undo done-all edit priority move search filter tags stats report"

    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=( $(compgen -W "${commands} --help --version" -- ${cur}) )
    else
        case "${COMP_WORDS[1]}" in
            add)
                if [[ ${cur} == -* ]]; then
                    COMPREPLY=( $(compgen -W "--priority -p --tag -t" -- ${cur}) )
                elif [[ ${prev} == "-p" ]] || [[ ${prev} == "--priority" ]]; then
                    COMPREPLY=( $(compgen -W "high medium low" -- ${cur}) )
                fi
                ;;
            ls)
                COMPREPLY=( $(compgen -W "--all -a" -- ${cur}) )
                ;;
            rm)
                COMPREPLY=( $(compgen -W "--confirm -y" -- ${cur}) )
                ;;
            clear)
                COMPREPLY=( $(compgen -W "--completed --active --force -f" -- ${cur}) )
                ;;
            edit)
                COMPREPLY=( $(compgen -W "--text -t --priority -p --add-tag --remove-tag" -- ${cur}) )
                ;;
            filter)
                COMPREPLY=( $(compgen -W "--priority -p --tag -t --completed -c --active -a" -- ${cur}) )
                ;;
            search)
                COMPREPLY=( $(compgen -W "--tag -t --priority -p --completed -c" -- ${cur}) )
                ;;
            stats)
                COMPREPLY=( $(compgen -W "--detailed -d" -- ${cur}) )
                ;;
            report)
                if [[ ${cur} == -* ]]; then
                    COMPREPLY=( $(compgen -W "--format -f --output -o" -- ${cur}) )
                elif [[ ${prev} == "-f" ]] || [[ ${prev} == "--format" ]]; then
                    COMPREPLY=( $(compgen -W "text json" -- ${cur}) )
                fi
                ;;
            tags)
                COMPREPLY=( $(compgen -W "--no-tags" -- ${cur}) )
                ;;
            priority)
                if [ $COMP_CWORD -eq 3 ]; then
                    COMPREPLY=( $(compgen -W "low medium high" -- ${cur}) )
                fi
                ;;
            *)
                COMPREPLY=()
                ;;
        esac
    fi
}
complete -F _tix_simple tix
BASH_COMPLETION_EOF

    COMPLETION_ADDED=true

elif [ "$SHELL_NAME" = "zsh" ] && [ -n "$CONFIG_FILE" ]; then
    if ! grep -q "_TIX_COMPLETE" "$CONFIG_FILE" 2>/dev/null; then
        echo "" >> "$CONFIG_FILE"
        echo "# TIX Command Completion" >> "$CONFIG_FILE"
        echo 'eval "$(_TIX_COMPLETE=zsh_source tix)"' >> "$CONFIG_FILE"
        COMPLETION_ADDED=true
    fi

elif [ "$SHELL_NAME" = "fish" ]; then
    FISH_COMPLETIONS="$HOME/.config/fish/completions"
    mkdir -p "$FISH_COMPLETIONS"
    cat > "$FISH_COMPLETIONS/tix.fish" << 'FISH_EOF'
# TIX Fish Completion
complete -c tix -f
complete -c tix -n "__fish_use_subcommand" -a "add ls done rm clear undo done-all edit priority move search filter tags stats report"
complete -c tix -n "__fish_use_subcommand" -l help -d "Show help"
complete -c tix -n "__fish_use_subcommand" -l version -d "Show version"
complete -c tix -n "__fish_seen_subcommand_from add" -s p -l priority -a "high medium low"
complete -c tix -n "__fish_seen_subcommand_from add" -s t -l tag -d "Add tag"
complete -c tix -n "__fish_seen_subcommand_from ls" -s a -l all -d "Show all tasks"
FISH_EOF
    COMPLETION_ADDED=true
fi

if [ "$COMPLETION_ADDED" = true ]; then
    echo -e "${GREEN}✅ Shell completion configured!${NC}"
else
    echo -e "${YELLOW}ℹ️  Completion setup skipped${NC}"
fi

# Final message
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         🎉 TIX Installation Complete! 🎉                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$SHELL_NAME" = "bash" ]; then
    echo -e "${BLUE}To activate TIX with tab completion:${NC}"
    echo -e "  ${YELLOW}source $CONFIG_FILE${NC}"
elif [ "$SHELL_NAME" = "zsh" ]; then
    echo -e "${BLUE}To activate TIX:${NC}"
    echo -e "  ${YELLOW}source ~/.zshrc${NC}"
elif [ "$SHELL_NAME" = "fish" ]; then
    echo -e "${BLUE}To activate TIX:${NC}"
    echo -e "  ${YELLOW}exec fish${NC}"
fi

echo ""
echo -e "${BLUE}Test completion:${NC}"
echo -e "  ${YELLOW}tix <TAB><TAB>${NC}  # Should show commands"
echo ""
echo -e "${BLUE}Quick start:${NC}"
echo -e "  ${YELLOW}tix add \"My first task\" -p high${NC}"
echo -e "  ${YELLOW}tix ls${NC}"
echo ""
echo -e "${BLUE}Happy task managing! 🚀${NC}"