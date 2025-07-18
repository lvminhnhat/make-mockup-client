import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Utility class for loading and managing JSON configuration files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigLoader with optional config file path.
        
        Args:
            config_path: Path to the config file. If None, will look for 'config.json' in project root.
        """
        if config_path is None:
            # Default to config.json in project root
            self.config_path = Path("config.json")
        else:
            self.config_path = Path(config_path)
    
    def load_config(self, create_if_missing: bool = True) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Args:
            create_if_missing: If True, create an empty config file if it doesn't exist.
            
        Returns:
            Dictionary containing configuration data.
            
        Raises:
            FileNotFoundError: If config file doesn't exist and create_if_missing is False.
            json.JSONDecodeError: If config file contains invalid JSON.
            PermissionError: If there are permission issues reading the file.
        """
        try:
            if not self.config_path.exists():
                if create_if_missing:
                    self._create_default_config()
                else:
                    raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
                
            return config_data if config_data else {}
            
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in config file {self.config_path}: {e.msg}",
                e.doc,
                e.pos
            )
        except PermissionError:
            raise PermissionError(f"Permission denied reading config file: {self.config_path}")
    
    def save_config(self, config_data: Dict[str, Any]) -> None:
        """
        Save configuration data to JSON file.
        
        Args:
            config_data: Dictionary containing configuration data to save.
            
        Raises:
            PermissionError: If there are permission issues writing the file.
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(config_data, file, indent=4, ensure_ascii=False)
                
        except PermissionError:
            raise PermissionError(f"Permission denied writing config file: {self.config_path}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation for nested keys, e.g., 'database.host').
            default: Default value to return if key is not found.
            
        Returns:
            Configuration value or default if not found.
        """
        config = self.load_config()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a specific configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation for nested keys).
            value: Value to set.
        """
        config = self.load_config()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
        
        self.save_config(config)
    
    def _create_default_config(self) -> None:
        """Create a default empty configuration file."""
        default_config = {
            "app": {
                "name": "Make Mockup Client",
                "version": "1.0.0"
            },
            "settings": {}
        }
        self.save_config(default_config)


# Convenience functions for quick usage
def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to load configuration from JSON file.
    
    Args:
        config_path: Path to config file. If None, uses default 'config.json'.
        
    Returns:
        Dictionary containing configuration data.
    """
    loader = ConfigLoader(config_path)
    return loader.load_config()


def get_config_value(key: str, default: Any = None, config_path: Optional[str] = None) -> Any:
    """
    Quick function to get a specific configuration value.
    
    Args:
        key: Configuration key (supports dot notation).
        default: Default value if key not found.
        config_path: Path to config file. If None, uses default 'config.json'.
        
    Returns:
        Configuration value or default.
    """
    loader = ConfigLoader(config_path)
    return loader.get_config_value(key, default)


def save_config(config_data: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """
    Quick function to save configuration data.
    
    Args:
        config_data: Configuration data to save.
        config_path: Path to config file. If None, uses default 'config.json'.
    """
    loader = ConfigLoader(config_path)
    loader.save_config(config_data)


def set_config_value(key: str, value: Any, config_path: Optional[str] = None) -> None:
    """
    Quick function to set a specific configuration value.
    
    Args:
        key: Configuration key (supports dot notation).
        value: Value to set.
        config_path: Path to config file. If None, uses default 'config.json'.
    """
    loader = ConfigLoader(config_path)
    loader.set_config_value(key, value)


# Example usage
if __name__ == "__main__":
    # Example 1: Using the ConfigLoader class
    config_loader = ConfigLoader()
    
    # Load config
    config = config_loader.load_config()
    print("Current config:", config)
    
    # Get specific value
    app_name = config_loader.get_config_value("app.name", "Default App")
    print(f"App name: {app_name}")
    
    # Set a value
    config_loader.set_config_value("settings.debug", True)
    
    # Example 2: Using convenience functions
    config_data = load_config()
    debug_mode = get_config_value("settings.debug", False)
    print(f"Debug mode: {debug_mode}")