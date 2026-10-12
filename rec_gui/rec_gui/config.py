"""Configuration management for rec_gui package."""

import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Values accepted by the rosbag2 MCAP storage plugin (--storage-config-file)
MCAP_COMPRESSION = {"none": "None", "lz4": "Lz4", "zstd": "Zstd"}
MCAP_COMPRESSION_LEVELS = ("Fastest", "Fast", "Default", "Slow", "Slowest")


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
                'max_cache_size': 1048576000,
                'mcap': {
                    'compression': 'zstd',
                    'compression_level': 'default',
                    'chunk_size': 52428800,
                },
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

    def get_storage_config_file(self, profile: str) -> Path:
        """Get the MCAP writer options file passed to --storage-config-file."""
        custom = self.get_profile(profile).get("storage_config_file")
        if custom:
            return Path(custom)
        safe_name = re.sub(r"[^\w.-]", "_", profile)
        return Path.home() / ".rec_gui" / f"mcap_writer_options_{safe_name}.yaml"

    def get_mcap_options(self, profile: str) -> Dict[str, Any]:
        """Get the MCAP writer options (chunkSize, compression, compressionLevel)."""
        profile_data = self.get_profile(profile)

        # A profile can point to its own writer options file
        custom = profile_data.get("storage_config_file")
        if custom and Path(custom).is_file():
            with open(custom, "r") as f:
                return yaml.safe_load(f) or {}

        defaults = self.get_nested("recording", "mcap") or {}

        def setting(key, fallback):
            return profile_data.get(key, defaults.get(key, fallback))

        compression = str(setting("compression", "zstd")).lower()
        level = str(setting("compression_level", "default")).capitalize()
        return {
            "chunkSize": int(setting("chunk_size", 52428800)),
            "compression": MCAP_COMPRESSION.get(compression, "Zstd"),
            "compressionLevel": level if level in MCAP_COMPRESSION_LEVELS else "Default",
        }

    def write_storage_config(self, profile: str) -> Path:
        """Write the MCAP writer options file, unless the profile brings its own."""
        path = self.get_storage_config_file(profile)
        if not self.get_profile(profile).get("storage_config_file"):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                yaml.dump(self.get_mcap_options(profile), f, default_flow_style=False)
        return path

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
        max_cache_size = self.get_profile(profile).get(
            "max_cache_size", self.get("recording.max_cache_size", 1048576000)
        )

        return [
            "ros2", "bag", "record",
            "-s", "mcap",
            "-o", str(output_dir / self.get_recording_name(profile, when)),
            "--max-cache-size", str(max_cache_size),
            "--storage-config-file", str(self.get_storage_config_file(profile)),
            *topics,
        ]
