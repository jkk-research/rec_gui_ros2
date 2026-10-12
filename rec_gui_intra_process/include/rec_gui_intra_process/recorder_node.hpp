/**
 * @file recorder_node.hpp
 * @brief Main MCAP recorder node with intra-process communication
 */

#ifndef REC_GUI_INTRA_PROCESS__RECORDER_NODE_HPP_
#define REC_GUI_INTRA_PROCESS__RECORDER_NODE_HPP_

#include <memory>
#include <string>
#include <vector>
#include <map>
#include <atomic>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_components/register_node_macro.hpp"

namespace rec_gui_intra_process
{

enum class RecordingState
{
  IDLE = 0,
  STARTING = 1,
  RECORDING = 2,
  PAUSED = 3,
  STOPPING = 4,
  ERROR = 5,
};

struct RecordingConfig
{
  std::vector<std::string> topics;
  std::string output_file;
  std::string compression;
  uint32_t chunk_size;
  std::string profile;
};

class RecorderNode : public rclcpp::Node
{
public:
  explicit RecorderNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
  virtual ~RecorderNode();

  /**
   * Start recording specified topics
   * @param config Recording configuration
   * @return true if recording started successfully
   */
  bool startRecording(const RecordingConfig & config);

  /**
   * Pause the current recording
   * @return true if recording was paused
   */
  bool pauseRecording();

  /**
   * Resume the current recording
   * @return true if recording was resumed
   */
  bool resumeRecording();

  /**
   * Stop the current recording
   * @return true if recording was stopped
   */
  bool stopRecording();

  /**
   * Get the current recording state
   * @return Current recording state
   */
  RecordingState getRecordingState() const;

  /**
   * Get available topics
   * @return Vector of available topic names
   */
  std::vector<std::string> getAvailableTopics() const;

private:
  void onTimer();
  void discoverTopics();

  RecordingConfig current_config_;
  std::atomic<RecordingState> recording_state_{RecordingState::IDLE};
  rclcpp::TimerBase::SharedPtr timer_;
  std::map<std::string, std::string> available_topics_;
  std::atomic<uint64_t> messages_recorded_{0};

  static constexpr int TOPIC_DISCOVERY_INTERVAL_MS = 2000;
};

}  // namespace rec_gui_intra_process

#endif  // REC_GUI_INTRA_PROCESS__RECORDER_NODE_HPP_
