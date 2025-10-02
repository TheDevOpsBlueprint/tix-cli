import os
import yaml
from typing import Any, Dict


DEFAULT_CONFIG = {
    'defaults': {
        'priority': 'medium',
        'tags': [],
    },
    'colors': {
        'priority': {
            'low': 'green',
            'medium': 'yellow',
            'high': 'red',
        },
        'status': {
            'active': 'blue',
            'completed': 'green',
        },
        'tags': 'cyan',
    },
    'aliases': {
        'l': 'ls',
        'a': 'add',
        'd': 'done',
        'r': 'rm',
        'e': 'edit',
        'p': 'priority',
        's': 'search',
        'f': 'filter',
    },
    'notifications': {
        'enabled': True,
        'on_creation': True,
        'on_update': True,
        'on_completion': True,
    },
    'display': {
        'show_ids': True,
        'show_dates': False,
        'compact_mode': False,
        'max_text_length': 0,  # 0 means no limit
    },
}


def get_config_path():
    """Get the path to the configuration file"""
    return os.path.expanduser('~/.tix/config.yml')


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.
    Nested dictionaries are merged recursively.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config():
    """Load configuration from file, merging with defaults"""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return DEFAULT_CONFIG.copy()

    if not user_config:
        return DEFAULT_CONFIG.copy()
    
    # Deep merge user config with defaults
    return deep_merge(DEFAULT_CONFIG, user_config)


def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    ensure_config_dir_exists()
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except (IOError, yaml.YAMLError) as e:
        print(f"Error: Failed to save config to {config_path}: {e}")
        return False


def ensure_config_dir_exists():
    """Ensure the configuration directory exists"""
    config_dir = os.path.dirname(get_config_path())
    os.makedirs(config_dir, exist_ok=True)


def create_default_config_if_not_exists():
    """Create default configuration file if it doesn't exist"""
    ensure_config_dir_exists()
    config_path = get_config_path()
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
        return True
    return False


def get_config_value(key_path: str, default=None):
    """
    Get a configuration value using dot notation.
    Example: get_config_value('colors.priority.high') returns 'red'
    """
    config = load_config()
    keys = key_path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def set_config_value(key_path: str, value: Any) -> bool:
    """
    Set a configuration value using dot notation.
    Example: set_config_value('defaults.priority', 'high')
    """
    config = load_config()
    keys = key_path.split('.')
    current = config
    
    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the value
    current[keys[-1]] = value
    return save_config(config)


# Global config instance
CONFIG = load_config()
