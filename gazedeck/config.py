"""Configuration settings for GazeDeck"""

import json
from pathlib import Path
from typing import Dict, Any
import os


class Config:
    """Configuration manager for GazeDeck"""
    
    def __init__(self):
        self.config_file = Path.home() / ".gazedeck" / "config.json"
        self._config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            "websocket": {
                "host": "localhost",
                "port": 8765
            },
            "fixation": {
                "duration_ms": 500
            },
            "screen": {
                "width": 1920,
                "height": 1080
            },
            "markers": {
                "size": 100,
                "margin": 50
            },
            "pupil": {
                "device_timeout": 10,
                "auto_connect": False
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Create default config
        default_config = self._get_default_config()
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation (e.g., 'websocket.host')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self._save_config(self._config)
    
    @property
    def websocket_host(self) -> str:
        return self.get('websocket.host', 'localhost')
    
    @property
    def websocket_port(self) -> int:
        return self.get('websocket.port', 8765)
    
    @property
    def fixation_duration_ms(self) -> int:
        return self.get('fixation.duration_ms', 500)


# Global config instance
config = Config()
