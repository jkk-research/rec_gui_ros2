# `rec_gui` - MCAP Recording GUI for ROS 2

A graphical user interface for recording and managing MCAP (Multi-CAN Artifact Protocol) recordings from ROS 2 topics.

## Features

- **GUI-based topic selection**: Browse and select available ROS 2 topics with a user-friendly interface
- **Recording profiles**: Pre-configured recording profiles (default, high compression, low latency)
- **Status indicators**: Real-time display of recording state and duration
- **YAML configuration**: Flexible configuration system for customizing behavior
- **MCAP format support**: Built-in support for MCAP recording format with chunk compression (storage presets)
- **Dark theme**: Modern dark UI with accent colors for better usability

## Prerequisites

- ROS 2 (Humble or later recommended)
- Python 3.8+
- tkinter (usually included with Python)
- CustomTkinter (`pip install customtkinter`)
- PyYAML

## Installation

### From Source

1. Clone the repository into your ROS 2 workspace:
```bash
cd ~/ros2_ws/src
git clone https://github.com/jkk-research/rec_gui_ros2.git
```

2. Install dependencies:
```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
```

3. Build the package using colcon:
```bash
colcon build --packages-select rec_gui
```

4. Source the setup file:
```bash
source ~/ros2_ws/install/setup.bash
```

## Building with Colcon

To build the complete workspace including `rec_gui`:

```bash
cd ~/ros2_ws
colcon build
```

To build only the `rec_gui` package:

```bash
colcon build --packages-select rec_gui
```

To build with verbose output:

```bash
colcon build --packages-select rec_gui --event-handlers console_direct+
```

## Running the GUI

### Basic Launch

After building and sourcing the setup, run the GUI with:

```bash
rec_gui
```

Or directly with Python:

```bash
python3 -m rec_gui.rec_gui_node
```

### Configuration

The application looks for configuration files in the following order:

1. `~/.rec_gui/rec_gui.yaml` (user config)
2. `/opt/rec_gui/rec_gui.yaml` (system config)
3. `<package_share>/resource/rec_gui.yaml` (default config)

To use a custom configuration file:

```bash
rec_gui --config /path/to/custom/rec_gui.yaml
```

## Configuration File

The YAML configuration file (`rec_gui.yaml`) contains settings for:

### Output Settings
```yaml
output:
  directory: "${HOME}/.rec_gui/recordings"
  output_prefix: "recording"            # <output_prefix>_<date_profile>.mcap
  date_profile: "yyyy-MM-dd_HH-mm-ss"   # yyyy yy MM dd HH mm ss (MM month, mm minutes) or %Y-%m-%d...
  daily_subfolder: false                # <directory>/2026_10_16_<profile>/
  auto_create: true
```

### Recording Profiles
```yaml
recording:
  profiles:
    default:
      description: "Default recording profile"
      topics: []
      storage_preset: "zstd_fast"  # overrides the value below

  # ros2 bag record options, profiles can override each of them
  max_cache_size: 5242880       # --max-cache-size, 5 MB
  storage_preset: "zstd_fast"   # --storage-preset-profile, zstd_* compress the MCAP chunks
```

### Topic Configuration
```yaml
topics:
  include: []  # Include patterns (regex)
  exclude: []  # Exclude patterns (regex)
  watch_enabled: true
  refresh_interval: 2
```

### GUI Settings
```yaml
gui:
  window_width: 1200
  window_height: 800
  auto_refresh_topics: true
  show_message_rates: true
  show_message_types: true
  log_file: "${HOME}/.rec_gui/logs/rec_gui.log"
  log_level: "INFO"
```

## Usage Guide

1. **Launch the application** using `rec_gui`
2. **View available topics** in the topic list panel
3. **Select topics** by checking the boxes next to topic names
   - Use "Select All" to select all topics
   - Use "Clear Selection" to deselect all topics
   - Use "Refresh Topics" to update the topic list
4. **Choose a recording profile** from the dropdown menu
5. **Start recording** by clicking the "▶ Start Recording" button
6. **Monitor recording** with the status indicator and duration display
7. **Pause recording** (if supported) by clicking the "⏸ Pause" button
8. **Stop recording** by clicking the "⏹ Stop Recording" button

## File Structure

```
rec_gui_ros2/
├── rec_gui/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration management
│   ├── recorder_gui.py          # GUI implementation
│   └── rec_gui_node.py          # ROS 2 node implementation
├── resource/
│   ├── rec_gui.yaml             # Default configuration
│   └── rec_gui                  # ROS 2 resource marker
├── package.xml                  # ROS 2 package manifest
├── setup.py                     # Python setup configuration
└── README.md                    # This file
```

## Architecture

### RecorderConfig
Manages application configuration with support for:
- YAML file loading
- Environment variable expansion
- Nested configuration access
- Configuration persistence

### RecorderGUI
Main GUI window featuring:
- Topic list with selection
- Recording controls
- Status indicators
- Duration tracking
- Information display

### RecRecorderNode
ROS 2 node handling:
- Topic discovery
- Recording management
- Node lifecycle

### RecordingState
Enumeration tracking recording states:
- IDLE: No recording active
- STARTING: Initializing recording
- RECORDING: Recording in progress
- PAUSED: Recording paused
- STOPPING: Stopping recording
- ERROR: Error state

## Color Palette

The GUI uses a modern dark theme:
- Background: `#0d0f14`
- Panel: `#13161e`
- Border: `#1e2330`
- Accent: `#00d4ff` (cyan)
- Orange: `#ff6b35`
- Good: `#00e676` (green)
- Warning: `#ffea00` (yellow)
- Bad: `#ff1744` (red)
- Text: `#e8eaf0`
- Muted: `#4a5068`

## Logging

Logs are written to `~/.rec_gui/logs/rec_gui.log` by default. Log level can be configured in the YAML file.

## Integration with rec_gui_intra_process

The `rec_gui` package is designed to work with the `rec_gui_intra_process` package for intra-process communication and efficient recording. This integration is planned for future development.

## Troubleshooting

### GUI doesn't appear
- Ensure tkinter is installed: `sudo apt install python3-tk`
- Check if X11/display is available: `echo $DISPLAY`

### Topics list is empty
- Verify ROS 2 network is working: `ros2 topic list`
- Check node parameters and configuration
- Ensure topics are being published on the same ROS domain

### Recording won't start
- Verify at least one topic is selected
- Check ROS 2 logs for errors
- Ensure output directory is writable

## Contributing

Contributions are welcome! Please follow ROS 2 coding standards and include tests for new features.

## License

This package is licensed under the Apache License 2.0. See the LICENSE file for details.

## Support

For issues, feature requests, or questions, please open an issue on the GitHub repository.
