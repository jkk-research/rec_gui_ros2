# REC GUI Intra-Process - C++ MCAP Recorder

High-performance C++ backend for MCAP recording with intra-process communication support for ROS 2.

## Overview

`rec_gui_intra_process` is a C++ ROS 2 package that provides the backend recording functionality for the `rec_gui` Python GUI. It uses intra-process communication to efficiently record ROS 2 messages to MCAP format files.

## Features

- **Intra-process Communication**: Zero-copy message passing between nodes in the same process
- **MCAP Format Support**: Write to MCAP format with configurable compression
- **Compression**: Support for zstd compression with configurable levels
- **Generic Topic Subscription**: Subscribe to topics of any type without code generation
- **Performance Optimized**: Thread-safe message recording with minimal overhead
- **Component-based**: Can be used as a standalone node or as a composable component
- **Topic Discovery**: Automatic topic discovery and type inference

## Architecture

### RecorderNode
Main ROS 2 node that:
- Discovers available topics
- Manages recording state
- Orchestrates topic listeners and MCAP writer
- Handles lifecycle events

### TopicListener
Generic subscription handler:
- Subscribes to arbitrary ROS 2 topics
- Uses serialized message format for type-agnostic recording
- Counts messages and tracks state

### MCAPWriter
MCAP file format writer:
- Opens/closes MCAP files
- Writes channel definitions
- Writes message records with timestamps
- Supports compression configuration

## Building

From the workspace root:

```bash
colcon build --packages-select rec_gui_intra_process
```

To build with verbose output:

```bash
colcon build --packages-select rec_gui_intra_process --event-handlers console_direct+
```

## Running

### Standalone Node

```bash
ros2 run rec_gui_intra_process mcap_recorder_node
```

### With Composition

```bash
ros2 run rclcpp_components component_container
# In another terminal
ros2 component load /ComponentManager rec_gui_intra_process rec_gui_intra_process::RecorderNode
```

## Configuration

The node reads configuration from `config/mcap_recorder.yaml`. Key settings:

- `recorder.output_dir`: Output directory for MCAP files
- `recorder.compression`: Compression type (none, zstd)
- `recorder.compression_level`: Compression level (1-22 for zstd)
- `recorder.chunk_size`: MCAP chunk size in bytes
- `subscription.qos_history_depth`: QoS history depth
- `performance.use_intra_process`: Enable intra-process communication

## API

### RecorderNode

```cpp
// Start recording
bool startRecording(const RecordingConfig & config);

// Pause recording
bool pauseRecording();

// Resume recording
bool resumeRecording();

// Stop recording
bool stopRecording();

// Get recording state
RecordingState getRecordingState() const;

// Get available topics
std::vector<std::string> getAvailableTopics() const;
```

### Recording Configuration

```cpp
struct RecordingConfig {
  std::vector<std::string> topics;    // Topics to record
  std::string output_file;             // Output file path
  std::string compression;             // Compression type
  uint32_t chunk_size;                 // Chunk size in bytes
  std::string profile;                 // Recording profile name
};
```

### Recording States

```cpp
enum class RecordingState {
  IDLE = 0,           // No recording
  STARTING = 1,       // Initializing recording
  RECORDING = 2,      // Recording active
  PAUSED = 3,         // Recording paused
  STOPPING = 4,       // Stopping recording
  ERROR = 5,          // Error state
};
```

## File Structure

```
rec_gui_intra_process/
├── include/rec_gui_intra_process/
│   ├── recorder_node.hpp        # Main recorder node
│   ├── topic_listener.hpp       # Generic topic listener
│   └── mcap_writer.hpp          # MCAP format writer
├── src/
│   ├── recorder_node.cpp        # Node implementation
│   ├── topic_listener.cpp       # Listener implementation
│   ├── mcap_writer.cpp          # Writer implementation
│   └── mcap_recorder_node_main.cpp  # Entry point
├── config/
│   └── mcap_recorder.yaml       # Configuration file
├── CMakeLists.txt               # Build configuration
└── package.xml                  # ROS 2 package manifest
```

## Dependencies

- rclcpp: ROS 2 C++ client library
- rclcpp_components: Component composition support
- std_msgs: Standard ROS 2 messages
- rosgraph_msgs: ROS graph messages

## Performance Considerations

1. **Intra-process Communication**: Enabled by default for zero-copy message passing
2. **Serialized Messages**: All subscriptions use serialized message format to avoid code generation
3. **Thread Safety**: Atomic state variables and locks for concurrent access
4. **Memory Buffering**: Configurable message queue size to balance latency vs. throughput

## Logging

Logs are written to `~/.rec_gui/logs/mcap_recorder.log` by default. Configure via `config/mcap_recorder.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "/path/to/log"
```

## MCAP Format

The MCAP files are written with:
- Magic header: `MCAP0`
- Channel definitions for each unique topic
- Message records with:
  - Channel ID
  - Timestamp (nanoseconds)
  - Serialized message data
- Footer with message count

## Future Enhancements

- [ ] Multi-threaded message writing
- [ ] Dynamic topic subscriptions during recording
- [ ] Message filtering and transformation
- [ ] Statistics collection and reporting
- [ ] Real MCAP library integration (mcap C++ library)
- [ ] ROS 2 service interfaces for remote control

## Troubleshooting

### Build failures
- Ensure all ROS 2 dependencies are installed
- Check CMake version compatibility (requires 3.16+)

### Recording failures
- Verify output directory exists and is writable
- Check topic names are correct
- Ensure topics are being published

### Performance issues
- Increase `chunk_size` for large messages
- Adjust `thread_pool_size` for CPU-bound systems
- Enable compression for disk I/O bound systems

## License

Apache License 2.0

## Contributing

Contributions welcome! Follow ROS 2 C++ style guidelines and include tests for new features.
