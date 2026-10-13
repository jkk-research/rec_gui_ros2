"""Configuration management for rec_gui package."""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ros2 bag record options, settable in recording: and overridable per profile
# (config key, command line flag, fallback)
RECORD_OPTIONS = (
    ("max_cache_size", "--max-cache-size", 5242880),
    ("storage_preset", "--storage-preset-profile", "zstd_fast"),
    ("compression_mode", "--compression-mode", "file"),
    ("compression_format", "--compression-format", "zstd"),
    ("compression_level", "--compression-level", "fastest"),
)
# Values offered by the GUI, an empty compression level leaves the flag out
STORAGE_PRESETS = ("none", "fastwrite", "zstd_fast", "zstd_small")
COMPRESSION_MODES = ("none", "file", "message")
COMPRESSION_LEVELS = ("", "fastest", "fast", "default", "slow", "slowest")


class RecorderConfig:
    """Manages configuration for the MCAP recording GUI."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Optional path to configuration file.
                        If not provided, searches default locations.
        """
        self.config: Dict[str, Any] = {}
        self.config_path: Optional[Path] = None
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None) -> None:
        """Load configuration from file."""
        if config_path:
            path = Path(config_path)
            if path.exists():
                self.config_path = path
                self._read_yaml(path)
                return

        # Default search paths
        search_paths = [
            Path.home() / '.rec_gui' / 'rec_gui.yaml',
            Path('/opt/rec_gui/rec_gui.yaml'),
            Path(__file__).parent.parent / 'resource' / 'rec_gui.yaml',
        ]

        # Add install share path (install/rec_gui/share/rec_gui/rec_gui.yaml)
        # From install/rec_gui/lib/python3.x/site-packages/rec_gui, go up 5 levels to install/rec_gui
        install_share = Path(__file__).parent.parent.parent.parent.parent / 'share' / 'rec_gui' / 'rec_gui.yaml'
        search_paths.append(install_share)

        for path in search_paths:
            if path.exists():
                self.config_path = path
                self._read_yaml(path)
                return

        self.config = self._get_default_config()

    def _read_yaml(self, path: Path) -> None:
        """Read YAML configuration file."""
        try:
            with open(path, 'r') as f:
                content = yaml.safe_load(f)
                if content:
                    self.config = self._expand_paths(content)
                else:
                    self.config = self._get_default_config()
        except Exception as e:
            print(f"Error reading config file {path}: {e}")
            self.config = self._get_default_config()

    @staticmethod
    def _expand_paths(config: Dict[str, Any]) -> Dict[str, Any]:
        """Expand environment variables in path values."""
        def expand_value(value):
            if isinstance(value, str):
                return os.path.expandvars(value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(v) for v in value]
            return value

        return expand_value(config)

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Return minimal default configuration (profiles must come from YAML)."""
        return {
            'output': {
                'directory': str(Path.home() / '.rec_gui' / 'recordings'),
                'filename_template': 'recording_{timestamp}.mcap',
                'auto_create': True,
            },
            'recording': {
                'profiles': {},  # Profiles ONLY from YAML
                'default_profile': 'default',
                'max_cache_size': 5242880,
                'storage_preset': 'zstd_fast',
                'compression_mode': 'file',
                'compression_format': 'zstd',
                'compression_level': 'fastest',
            },
            'topics': {
                'include': [],
                'exclude': [],
                'watch_enabled': True,
                'refresh_interval': 2,
            },
            'gui': {
                'window_width': 1200,
                'window_height': 800,
                'auto_refresh_topics': True,
                'show_message_rates': True,
                'show_message_types': True,
                'log_file': str(Path.home() / '.rec_gui' / 'logs' / 'rec_gui.log'),
                'log_level': 'INFO',
            },
            'ros2': {
                'node_name': 'rec_gui',
                'qos_history_depth': 100,
                'use_intra_process': True,
            },
            'advanced': {
                'experimental_features': False,
                'max_concurrent_recordings': 1,
                'save_config_on_exit': True,
                'confirm_delete': True,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'output.directory')."""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_nested(self, *keys: str) -> Any:
        """Get nested configuration value."""
        return self.get('.'.join(keys))

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path
        if not save_path:
            save_path = Path.home() / '.rec_gui' / 'rec_gui.yaml'

        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            self.config_path = Path(save_path)
        except Exception as e:
            print(f"Error saving config to {save_path}: {e}")

    def get_output_directory(self) -> Path:
        """Get the output directory path (does not create it)."""
        return Path(self.get('output.directory'))

    def get_log_directory(self) -> Path:
        """Get the log directory, creating it if necessary."""
        log_file = Path(self.get('gui.log_file'))
        directory = log_file.parent
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def get_profile(self, name: str) -> Dict[str, Any]:
        """Get the settings of a recording profile (empty if unknown)."""
        profiles = self.get_nested("recording", "profiles") or {}
        return profiles.get(name) or {}

    def reload_profile(self, name: str) -> Dict[str, Any]:
        """Read a profile from the YAML file again, dropping unsaved changes."""
        try:
            with open(self.config_path, 'r') as f:
                content = self._expand_paths(yaml.safe_load(f) or {})
            profile = ((content.get("recording") or {}).get("profiles") or {}).get(name)
        except Exception as e:
            print(f"Error reading config file {self.config_path}: {e}")
            profile = None

        # Not in the file (or no file), keep what is loaded
        if profile:
            self.config.setdefault("recording", {}).setdefault("profiles", {})[name] = profile
        return self.get_profile(name)

    def get_record_options(self, profile: str) -> Dict[str, Any]:
        """Get the ros2 bag record options of a profile, keyed by config key."""
        profile_data = self.get_profile(profile)
        defaults = self.get_nested("recording") or {}

        options = {}
        for key, _, fallback in RECORD_OPTIONS:
            value = profile_data.get(key, defaults.get(key, fallback))
            options[key] = fallback if value is None else value
        return options

    def set_record_option(self, profile: str, key: str, value: Any) -> None:
        """Set a ros2 bag record option of a profile (not saved to file)."""
        profiles = self.config.setdefault("recording", {}).setdefault("profiles", {})
        if not profiles.get(profile):
            profiles[profile] = {}
        profiles[profile][key] = value

    def get_record_arguments(self, profile: str) -> List[str]:
        """Get the ros2 bag record arguments of a profile, unset options left out."""
        options = self.get_record_options(profile)
        compressing = str(options["compression_mode"]).lower() != "none"

        arguments = []
        for key, flag, _ in RECORD_OPTIONS:
            value = str(options[key]).strip()
            if not value:
                continue
            # A compression format is only valid together with a compression mode
            if key == "compression_format" and not compressing:
                continue
            arguments += [flag, value]
        return arguments

    def get_recording_name(self, profile: str, when: Optional[datetime] = None) -> str:
        """Get the name of the next recording, placeholders filled in."""
        when = when or datetime.now()
        profile_data = self.get_profile(profile)

        template = profile_data.get("filename_template")
        if not template and "output_prefix" in profile_data:
            template = f"{profile_data['output_prefix']}{{timestamp}}.mcap"
        if not template:
            template = self.get("output.filename_template", "recording_{timestamp}.mcap")

        date = when.strftime("%Y_%m_%d")
        time = when.strftime("%H_%M_%S")
        return (
            template.replace("{timestamp}", f"{date}-{time}")
            .replace("{date}", date)
            .replace("{time}", time)
        )

    def build_record_command(
        self,
        topics: List[str],
        profile: str,
        output_dir: Optional[str] = None,
        when: Optional[datetime] = None,
    ) -> List[str]:
        """Build the ros2 bag record command used for a recording."""
        output_dir = Path(output_dir or self.get_output_directory())

        return [
            "ros2", "bag", "record",
            "-s", "mcap",
            "-o", str(output_dir / self.get_recording_name(profile, when)),
            *self.get_record_arguments(profile),
            *topics,
        ]
