import os
import tempfile
import pytest
import yaml
from pathlib import Path
from tix.config import (
    DEFAULT_CONFIG,
    get_config_path,
    load_config,
    save_config,
    deep_merge,
    get_config_value,
    set_config_value,
    ensure_config_dir_exists,
    create_default_config_if_not_exists,
)


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create a temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, '.tix', 'config.yml')
        monkeypatch.setattr('tix.config.get_config_path', lambda: config_path)
        yield tmpdir


class TestDeepMerge:
    """Test deep merge functionality"""
    
    def test_simple_merge(self):
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = deep_merge(base, override)
        assert result == {'a': 1, 'b': 3, 'c': 4}
    
    def test_nested_merge(self):
        base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        override = {'a': {'y': 5, 'z': 6}, 'c': 7}
        result = deep_merge(base, override)
        assert result == {'a': {'x': 1, 'y': 5, 'z': 6}, 'b': 3, 'c': 7}
    
    def test_deep_nested_merge(self):
        base = {'level1': {'level2': {'level3': {'a': 1, 'b': 2}}}}
        override = {'level1': {'level2': {'level3': {'b': 3, 'c': 4}}}}
        result = deep_merge(base, override)
        assert result == {'level1': {'level2': {'level3': {'a': 1, 'b': 3, 'c': 4}}}}
    
    def test_override_with_non_dict(self):
        base = {'a': {'x': 1}, 'b': 2}
        override = {'a': 'string', 'b': {'y': 3}}
        result = deep_merge(base, override)
        assert result == {'a': 'string', 'b': {'y': 3}}


class TestConfigPath:
    """Test configuration path functions"""
    
    def test_get_config_path(self):
        path = get_config_path()
        assert path.endswith('.tix/config.yml')
        assert os.path.expanduser('~') in path
    
    def test_ensure_config_dir_exists(self, temp_config_dir):
        from tix.config import get_config_path
        config_path = get_config_path()
        config_dir = os.path.dirname(config_path)
        
        # Directory shouldn't exist yet
        assert not os.path.exists(config_dir)
        
        ensure_config_dir_exists()
        
        # Directory should now exist
        assert os.path.exists(config_dir)
        assert os.path.isdir(config_dir)


class TestLoadSaveConfig:
    """Test loading and saving configuration"""
    
    def test_load_config_no_file(self, temp_config_dir):
        """Should return default config when file doesn't exist"""
        config = load_config()
        assert config == DEFAULT_CONFIG
    
    def test_save_and_load_config(self, temp_config_dir):
        """Should save and load config correctly"""
        test_config = {
            'defaults': {'priority': 'high', 'tags': ['test']},
            'colors': {'priority': {'high': 'blue'}},
        }
        
        assert save_config(test_config)
        loaded_config = load_config()
        
        # Should merge with defaults
        assert loaded_config['defaults']['priority'] == 'high'
        assert loaded_config['defaults']['tags'] == ['test']
        assert loaded_config['colors']['priority']['high'] == 'blue'
        # Should still have default values for unspecified keys
        assert 'medium' in loaded_config['colors']['priority']
    
    def test_create_default_config(self, temp_config_dir):
        """Should create default config file"""
        from tix.config import get_config_path
        config_path = get_config_path()
        
        assert not os.path.exists(config_path)
        
        result = create_default_config_if_not_exists()
        assert result is True
        assert os.path.exists(config_path)
        
        # Should not create again
        result = create_default_config_if_not_exists()
        assert result is False
    
    def test_load_config_with_invalid_yaml(self, temp_config_dir):
        """Should return defaults when YAML is invalid"""
        from tix.config import get_config_path
        config_path = get_config_path()
        ensure_config_dir_exists()
        
        # Write invalid YAML
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        config = load_config()
        assert config == DEFAULT_CONFIG


class TestConfigValues:
    """Test getting and setting config values"""
    
    def test_get_config_value_simple(self, temp_config_dir):
        """Should get simple config value"""
        test_config = {'defaults': {'priority': 'high'}}
        save_config(test_config)
        
        value = get_config_value('defaults.priority')
        assert value == 'high'
    
    def test_get_config_value_nested(self, temp_config_dir):
        """Should get nested config value"""
        test_config = {'colors': {'priority': {'high': 'red'}}}
        save_config(test_config)
        
        value = get_config_value('colors.priority.high')
        assert value == 'red'
    
    def test_get_config_value_not_found(self, temp_config_dir):
        """Should return default when key not found"""
        value = get_config_value('nonexistent.key', default='fallback')
        assert value == 'fallback'
    
    def test_set_config_value_simple(self, temp_config_dir):
        """Should set simple config value"""
        result = set_config_value('defaults.priority', 'low')
        assert result is True
        
        value = get_config_value('defaults.priority')
        assert value == 'low'
    
    def test_set_config_value_nested(self, temp_config_dir):
        """Should set nested config value"""
        result = set_config_value('colors.priority.critical', 'purple')
        assert result is True
        
        value = get_config_value('colors.priority.critical')
        assert value == 'purple'
    
    def test_set_config_value_creates_path(self, temp_config_dir):
        """Should create intermediate keys if they don't exist"""
        result = set_config_value('new.nested.key', 'value')
        assert result is True
        
        value = get_config_value('new.nested.key')
        assert value == 'value'
    
    def test_set_config_value_different_types(self, temp_config_dir):
        """Should handle different value types"""
        # Boolean
        set_config_value('test.bool', True)
        assert get_config_value('test.bool') is True
        
        # Integer
        set_config_value('test.int', 42)
        assert get_config_value('test.int') == 42
        
        # List
        set_config_value('test.list', ['a', 'b', 'c'])
        assert get_config_value('test.list') == ['a', 'b', 'c']
        
        # Dict
        set_config_value('test.dict', {'x': 1, 'y': 2})
        assert get_config_value('test.dict') == {'x': 1, 'y': 2}


class TestDefaultConfig:
    """Test default configuration structure"""
    
    def test_default_config_structure(self):
        """Should have all required keys"""
        assert 'defaults' in DEFAULT_CONFIG
        assert 'colors' in DEFAULT_CONFIG
        assert 'aliases' in DEFAULT_CONFIG
        assert 'notifications' in DEFAULT_CONFIG
        assert 'display' in DEFAULT_CONFIG
    
    def test_default_config_defaults(self):
        """Should have correct default values"""
        # Check that defaults section exists and has expected structure
        assert 'priority' in DEFAULT_CONFIG['defaults']
        assert 'tags' in DEFAULT_CONFIG['defaults']
        assert isinstance(DEFAULT_CONFIG['defaults']['tags'], list)
    
    def test_default_config_colors(self):
        """Should have color definitions"""
        assert 'priority' in DEFAULT_CONFIG['colors']
        assert 'status' in DEFAULT_CONFIG['colors']
        assert 'tags' in DEFAULT_CONFIG['colors']
        
        # Check priority colors
        assert 'low' in DEFAULT_CONFIG['colors']['priority']
        assert 'medium' in DEFAULT_CONFIG['colors']['priority']
        assert 'high' in DEFAULT_CONFIG['colors']['priority']
    
    def test_default_config_aliases(self):
        """Should have command aliases"""
        aliases = DEFAULT_CONFIG['aliases']
        assert 'l' in aliases
        assert 'a' in aliases
        assert 'd' in aliases
    
    def test_default_config_notifications(self):
        """Should have notification settings"""
        notif = DEFAULT_CONFIG['notifications']
        assert 'enabled' in notif
        assert 'on_creation' in notif
        assert 'on_update' in notif
        assert 'on_completion' in notif
    
    def test_default_config_display(self):
        """Should have display settings"""
        display = DEFAULT_CONFIG['display']
        assert 'show_ids' in display
        assert 'show_dates' in display
        assert 'compact_mode' in display
        assert 'max_text_length' in display


class TestConfigIntegration:
    """Integration tests for config functionality"""
    
    def test_full_config_workflow(self, temp_config_dir):
        """Test complete config workflow"""
        # 1. Create default config
        assert create_default_config_if_not_exists()
        
        # 2. Load and verify defaults exist
        config = load_config()
        assert 'defaults' in config
        assert 'priority' in config['defaults']
        original_priority = config['defaults']['priority']
        
        # 3. Modify a value
        set_config_value('defaults.priority', 'high')
        
        # 4. Verify change persisted
        config = load_config()
        assert config['defaults']['priority'] == 'high'
        
        # 5. Add new nested value
        set_config_value('custom.setting', 'value')
        
        # 6. Verify new value exists
        assert get_config_value('custom.setting') == 'value'
        
        # 7. Reset to defaults
        save_config(DEFAULT_CONFIG)
        config = load_config()
        assert config['defaults']['priority'] == DEFAULT_CONFIG['defaults']['priority']
        assert get_config_value('custom.setting') is None
