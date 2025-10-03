# TIX - Lightning-fast Terminal Task Manager ⚡

A minimalist, powerful command-line task manager built with Python. Manage your todos efficiently without leaving your terminal.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Shell Completion](https://img.shields.io/badge/completion-auto--enabled-success.svg)
![One-Command Install](https://img.shields.io/badge/install-one--command-ff69b4.svg)
![PEP 668](https://img.shields.io/badge/PEP--668-compatible-green.svg)

## 🚀 Quick Install (One Command!)

```bash
curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash
```

**That's it!** This smart installer (v8.0) will:
- ✅ Detect your OS and shell automatically
- ✅ Handle Python 3.12+ managed environments (PEP 668)
- ✅ Install using pipx for isolation (recommended)
- ✅ Configure shell completion automatically
- ✅ Set up PATH correctly
- ✅ Offer to restart your shell with everything ready

After installation, you can immediately use:
```bash
tix <TAB><TAB>  # Tab completion works!
tix add "My task"  # Start managing tasks!
```

## ✨ Features

- **Fast & Simple**: Add tasks with a single command
- **Smart Installation**: One-command setup that handles all environments
- **Python 3.12+ Compatible**: Works with externally-managed environments
- **Persistent Storage**: Tasks are saved locally in JSON format
- **Priority Levels**: Organize tasks by high, medium, or low priority
- **Tags**: Categorize tasks with custom tags
- **Search & Filter**: Find tasks quickly with powerful search
- **Statistics**: Track your productivity with built-in analytics
- **Reports**: Export your tasks in text or JSON format
- **Colored Output**: Beautiful terminal UI with rich formatting
- **Bulk Operations**: Mark multiple tasks as done at once
- **Auto Shell Completion**: Tab completion works out of the box for bash, zsh, and fish
- **Attachments & Links**: Attach files or add reference URLs to tasks
- **Open Attachments**: Use `tix open <id>` to quickly open all files/links for a task
- **Customizable Configuration**: Personalize defaults, colors, aliases, and notifications via `~/.tix/config.yml`
- **Interactive TUI**: Launch a full-screen terminal interface for task management

## 📖 Installation Methods

### Recommended: One-Command Install

Works on macOS, Linux, and WSL with Python 3.7+:

```bash
curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash
```

### macOS with Homebrew Python (Python 3.12+)

For macOS users with Homebrew-installed Python:

```bash
# Option 1: Install pipx first (recommended)
brew install pipx
pipx ensurepath
pipx install tix-cli

# Option 2: Use the smart installer (handles everything)
curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash
```

### Using pipx (Recommended for Python 3.12+)

```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install TIX
pipx install tix-cli
```

### Using pip with Virtual Environment

```bash
# Create virtual environment
python3 -m venv tix-env
source tix-env/bin/activate

# Install TIX
pip install tix-cli
```

### From Source

```bash
# Clone
git clone https://github.com/TheDevOpsBlueprint/tix-cli.git
cd tix-cli

# Run installer (handles all environments)
./install.sh

# Or use Make
make  # Runs smart installer
```

### For Developers

```bash
git clone https://github.com/TheDevOpsBlueprint/tix-cli.git
cd tix-cli

# Quick install for development
make quick-install

# Or with virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## 🎯 Troubleshooting Installation

### Python "Externally Managed Environment" Error

If you see this error on Python 3.12+:
```
error: externally-managed-environment
```

**Solution 1: Use the smart installer (recommended)**
```bash
curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash
```

**Solution 2: Use pipx**
```bash
brew install pipx  # on macOS
pipx install tix-cli
```

**Solution 3: Use virtual environment**
```bash
python3 -m venv tix-env
source tix-env/bin/activate
pip install tix-cli
```

### PATH Issues

If `tix` command is not found after installation:

```bash
# Add to your shell config (~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Then reload
source ~/.bashrc  # or ~/.zshrc
```

## 🎯 Usage Guide

### Basic Commands

#### Adding Tasks

```bash
# Simple task
tix add "Write documentation"

# With priority (high/medium/low)
tix add "Fix critical bug" -p high

# With tags
tix add "Review PR" -t work -t urgent

# Multiple tags and priority
tix add "Deploy to production" -p high -t devops -t release

# With file attachments (can repeat)
tix add "Review design doc" -f ~/docs/design.pdf -f ~/notes.txt

# With reference links (can repeat)
tix add "Research API" -l https://api.example.com -l https://swagger.io
```

#### Listing Tasks

```bash
# Show active tasks
tix ls

# Show all tasks (including completed)
tix ls --all
tix ls -a
```

#### Completing Tasks

```bash
# Mark single task as done
tix done 1

# Mark multiple tasks as done
tix done-all 1 3 5

# Undo completion (reactivate)
tix undo 1
```

#### Removing Tasks

```bash
# Remove a single task
tix rm 1

# Force remove without confirmation
tix rm 2 --confirm
tix rm 2 -y

# Clear all completed tasks
tix clear --completed

# Clear all active tasks (careful!)
tix clear --active --force
```

### Advanced Features

#### Editing Tasks

```bash
# Change task text
tix edit 1 --text "Updated task description"

# Change priority
tix priority 1 high

# Add/remove tags
tix edit 1 --add-tag urgent --remove-tag low-priority

# Multiple edits at once
tix edit 1 --text "New text" --priority high --add-tag important

# Add attachments and links to an existing task
tix edit 1 -f ~/extra.docx -l https://extra-resource.com
```

#### Searching and Filtering

```bash
# Search by text
tix search "bug"

# Search with filters
tix search "api" -p high -t backend

# Filter by criteria
tix filter -p high           # High priority tasks
tix filter -t urgent         # Tasks tagged "urgent"
tix filter --active          # Only active tasks
tix filter -a                # Short form for active
tix filter --completed       # Only completed tasks
tix filter -c                # Short form for completed

# List all tags
tix tags

# Show untagged tasks
tix tags --no-tags
```

#### Opening Attachments and Links

```bash
# Open all files and links attached to a task
tix open 1
```

#### Statistics and Reports

```bash
# View statistics
tix stats

# Detailed statistics
tix stats --detailed
tix stats -d

# Generate text report
tix report

# Export as JSON
tix report --format json --output tasks.json
tix report -f json -o tasks.json

# Export as text file
tix report --output my-tasks.txt
```

### 🔒 Backup & Restore
*All destructive operations (rm, clear) automatically create a backup before execution*

#### Creating Backups

```bash
# Create a timestamped backup
tix backup create

# Create a backup with a custom filename
tix backup create my-backup.json
```

#### Listing Backups

```bash
# List all available backups
tix backup list
```

#### Restoring From Backup

```bash
# Restore using top-level command (prompts for confirmation)
tix restore <file_name>

# Skip confirmation
tix restore <file_name> -y

# Equivalent grouped command
tix backup restore <file_name>
```


## 🎨 Using Tab Completion

Tab completion works automatically after installation:

```bash
# Complete commands
tix <TAB><TAB>
# Shows: add clear done done-all edit filter ls move priority report rm search stats tags undo

# Complete options
tix add --<TAB><TAB>
# Shows: --priority --tag --help

# Complete option values
tix add --priority <TAB><TAB>
# Shows: high low medium
```

## 📁 Data Storage

Tasks are stored in `~/.tix/tasks.json` in your home directory.

Example structure:
```json
{
  "next_id": 4,
  "tasks": [
    {
      "id": 1,
      "text": "Fix critical bug",
      "priority": "high",
      "completed": false,
      "created_at": "2025-01-17T10:30:00",
      "completed_at": null,
      "tags": ["bug", "urgent"]
    }
  ]
}
```

## 🎨 Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `add` | Add a new task | `tix add "Task" -p high -t work -f file.txt -l https://example.com` |
| `ls` | List tasks | `tix ls --all` |
| `done` | Complete a task | `tix done 1` |
| `done-all` | Complete multiple tasks | `tix done-all 1 2 3` |
| `rm` | Remove a task | `tix rm 1 -y` |
| `clear` | Clear tasks in bulk | `tix clear --completed` |
| `edit` | Edit task properties | `tix edit 1 --text "New" -f notes.md -l https://example.com` |
| `priority` | Change task priority | `tix priority 1 high` |
| `move` | Change task ID | `tix move 1 10` |
| `undo` | Reactivate completed task | `tix undo 1` |
| `search` | Search tasks by text | `tix search "bug"` |
| `filter` | Filter by criteria | `tix filter -p high` |
| `tags` | List all tags | `tix tags` |
| `stats` | Show statistics | `tix stats -d` |
| `report` | Generate report | `tix report -f json -o tasks.json` |
| `open` | Open attachments and links for a task | `tix open 1` |
| `config` | Manage configuration | `tix config show`, `tix config set defaults.priority high` |
| `interactive` | Launch interactive TUI | `tix interactive` |

## 🗑️ Uninstalling TIX

### Complete Uninstall

To completely remove TIX from your system:

```bash
# If installed from source with Makefile
make uninstall

# Or manually uninstall based on installation method
```

#### If installed with pipx:
```bash
pipx uninstall tix-cli
rm -rf ~/.tix  # Remove task data (optional)
```

#### If installed with pip:
```bash
pip uninstall tix-cli -y
# or
pip3 uninstall tix-cli -y
rm -rf ~/.tix  # Remove task data (optional)
```

#### If installed in virtual environment:
```bash
# Deactivate and remove the virtual environment
deactivate
rm -rf tix-env  # or whatever you named your venv
rm -rf ~/.tix  # Remove task data (optional)
```

#### Clean up shell configuration (optional):
```bash
# Remove TIX completion from your shell config
# For bash: edit ~/.bashrc or ~/.bash_profile
# For zsh: edit ~/.zshrc
# For fish: rm ~/.config/fish/completions/tix.fish

# Remove lines containing:
# - TIX Completion
# - _tix_simple
# - complete -F _tix_simple tix
```

#### Backup your tasks before uninstalling:
```bash
# Save your tasks before removing TIX
tix report -f json -o my-tasks-backup.json
# or
cp ~/.tix/tasks.json my-tasks-backup.json
```

## 🔧 Configuration

TIX supports extensive customization through a YAML configuration file located at `~/.tix/config.yml`.

### Quick Start

Initialize the configuration file with defaults:

```bash
tix config init
```

Or manually create `~/.tix/config.yml` using the example below.

### Configuration Options

#### Defaults

Set default values for new tasks:

```yaml
defaults:
  priority: medium  # Default priority: low, medium, high
  tags: []          # Default tags to add to every task
```

Example with default tags:
```yaml
defaults:
  priority: high
  tags:
    - work
    - urgent
```

#### Colors

Customize terminal colors:

```yaml
colors:
  priority:
    low: green
    medium: yellow
    high: red
  status:
    active: blue
    completed: green
  tags: cyan
```

#### Aliases

Create shortcuts for commands:

```yaml
aliases:
  l: ls          # tix l → tix ls
  a: add         # tix a "task" → tix add "task"
  d: done        # tix d 1 → tix done 1
  r: rm          # tix r 1 → tix rm 1
  e: edit        # tix e 1 → tix edit 1
  p: priority    # tix p 1 high → tix priority 1 high
  s: search      # tix s "query" → tix search "query"
  f: filter      # tix f -p high → tix filter -p high
```

#### Notifications

Control notification verbosity:

```yaml
notifications:
  enabled: true          # Master switch
  on_creation: true      # Show when creating tasks
  on_update: true        # Show detailed updates
  on_completion: true    # Show when completing tasks
```

#### Display

Customize task list appearance:

```yaml
display:
  show_ids: true         # Show task IDs
  show_dates: false      # Show creation dates
  compact_mode: false    # Compact view (hide tags column)
  max_text_length: 0     # Truncate text (0 = no limit)
```

### Configuration Commands

```bash
# Initialize config file
tix config init

# Show current configuration
tix config show

# Show specific config value
tix config show -k defaults.priority

# Set a configuration value
tix config set defaults.priority high
tix config set defaults.tags "[work, urgent]"

# Get a configuration value
tix config get defaults.priority

# Edit config in your default editor
tix config edit

# Show config file path
tix config path

# Reset to defaults
tix config reset
tix config reset -y  # Skip confirmation
```

### Example Configuration

See `config.example.yml` in the repository for a complete example with comments.

### Environment Variables

```bash
# Set custom storage location (optional)
export TIX_HOME=/custom/path
```

### PATH Configuration

Make sure `~/.local/bin` is in your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

## 🧪 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/TheDevOpsBlueprint/tix-cli.git
cd tix-cli

# Use make for easy setup
make setup  # Creates venv and installs everything

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Run tests
make test
# Or
pytest tests/ -v

# Run with coverage
make test-coverage
# Or
pytest tests/ -v --cov=tix --cov-report=term-missing
```

### Project Structure

```
tix-cli/
├── install.sh              # Smart installer v8.0 (PEP 668 compatible)
├── tix/
│   ├── __init__.py
│   ├── cli.py              # Main CLI with auto-completion
│   ├── models.py           # Task data model
│   ├── commands/
│   │   ├── __init__.py
│   │   └── stats.py        # Statistics module
│   └── storage/
│       ├── __init__.py
│       └── json_storage.py # Storage backend
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_models.py
│   ├── test_storage.py
│   └── test_completion.py
├── setup.py                # Package configuration
├── Makefile               # Developer commands
├── requirements.txt
├── pyproject.toml         # Python tooling config
├── .flake8               # Linting configuration
└── README.md
```

### CI/CD Pipeline

The project includes GitHub Actions workflows for:
- Testing across Python 3.8-3.12
- Code quality checks (flake8, black, isort)
- Building distribution packages
- Installation testing on Ubuntu and macOS
- Coverage reporting with Codecov

## 📝 Examples

### Daily Workflow

```bash
# Morning: Add today's tasks
tix add "Team standup meeting" -p high -t work
tix add "Review pull requests" -p medium -t work
tix add "Fix login bug" -p high -t bug -t urgent
tix add "Update documentation" -p low -t docs

# Check your tasks
tix ls

# Complete tasks
tix done 1
tix done 3

# End of day: View progress
tix stats

# Generate report
tix report --output daily-report.txt
```

### Project Management

```bash
# Add project tasks with tags
tix add "Design database schema" -p high -t project-x -t backend
tix add "Create API endpoints" -p high -t project-x -t backend
tix add "Write unit tests" -p medium -t project-x -t testing
tix add "Setup CI/CD pipeline" -p medium -t project-x -t devops

# View project tasks
tix filter -t project-x

# Search within project
tix search "API" -t project-x
```

## 🛠 Common Issues and Solutions

### Installation Issues

**Issue: "externally-managed-environment" error**
- Use the smart installer: `curl -sSL .../install.sh | bash`
- Or use pipx: `pipx install tix-cli`

**Issue: `tix: command not found`**
```bash
# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Issue: Permission denied**
```bash
# Use user installation
pip install --user tix-cli
```

### Shell Completion Issues

**Issue: Tab completion not working**
```bash
# For bash, check if completion is loaded
grep "_tix_simple" ~/.bashrc

# If not found, re-run installer
curl -sSL https://raw.githubusercontent.com/TheDevOpsBlueprint/tix-cli/main/install.sh | bash

# Or manually add completion (bash)
source ~/.bashrc
```

### Data Issues

**Issue: Tasks not persisting**
```bash
# Check storage file exists
ls -la ~/.tix/tasks.json

# Check permissions
chmod 644 ~/.tix/tasks.json
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Keep changes focused and small
4. Write tests for new features
5. Ensure all tests pass (`make test`)
6. Submit a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework with native completion support
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Python](https://python.org/) - Programming language

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TheDevOpsBlueprint/tix-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheDevOpsBlueprint/tix-cli/discussions)
- **Email**: valentin.v.todorov@gmail.com

## 🌟 Star History

If you find TIX useful, please consider giving it a star on GitHub!

[![Star History](https://img.shields.io/github/stars/TheDevOpsBlueprint/tix-cli?style=social)](https://github.com/TheDevOpsBlueprint/tix-cli)

---

**Made with ❤️ by TheDevOpsBlueprint**

*Enjoy lightning-fast task management with TIX!*