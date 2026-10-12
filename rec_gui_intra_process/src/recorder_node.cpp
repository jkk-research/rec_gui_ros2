/**
 * @file recorder_node.cpp
 * @brief Implementation of the MCAP recorder node
 */

#include "rec_gui_intra_process/recorder_node.hpp"
#include "rec_gui_intra_process/topic_listener.hpp"
#include "rec_gui_intra_process/mcap_writer.hpp"

#include <algorithm>
#include <chrono>
#include <thread>

namespace rec_gui_intra_process
{

RecorderNode::RecorderNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("mcap_recorder", options)
{
  RCLCPP_INFO(this->get_logger(), "Initializing MCAP Recorder Node");

  this->declare_parameter<std::string>("output_dir", std::string(getenv("HOME")) + "/.rec_gui/recordings");
  this->declare_parameter<std::string>("compression", "zstd");
  this->declare_parameter<int>("chunk_size", 52428800);

  timer_ = this->create_wall_timer(
    std::chrono::milliseconds(TOPIC_DISCOVERY_INTERVAL_MS),
    std::bind(&RecorderNode::onTimer, this));

  discoverTopics();
}

RecorderNode::~RecorderNode()
{
  if (recording_state_ == RecordingState::RECORDING) {
    stopRecording();
  }
}

bool RecorderNode::startRecording(const RecordingConfig & config)
{
  if (recording_state_ != RecordingState::IDLE) {
    RCLCPP_WARN(this->get_logger(), "Recording already in progress");
    return false;
  }

  recording_state_ = RecordingState::STARTING;
  current_config_ = config;

  RCLCPP_INFO(
    this->get_logger(),
    "Starting recording of %lu topics to %s",
    config.topics.size(),
    config.output_file.c_str());

  for (const auto & topic : config.topics) {
    RCLCPP_DEBUG(this->get_logger(), "Recording topic: %s", topic.c_str());
  }

  recording_state_ = RecordingState::RECORDING;
  messages_recorded_ = 0;

  return true;
}

bool RecorderNode::pauseRecording()
{
  if (recording_state_ != RecordingState::RECORDING) {
    RCLCPP_WARN(this->get_logger(), "No active recording to pause");
    return false;
  }

  recording_state_ = RecordingState::PAUSED;
  RCLCPP_INFO(this->get_logger(), "Recording paused. Messages recorded: %lu", messages_recorded_.load());

  return true;
}

bool RecorderNode::resumeRecording()
{
  if (recording_state_ != RecordingState::PAUSED) {
    RCLCPP_WARN(this->get_logger(), "No paused recording to resume");
    return false;
  }

  recording_state_ = RecordingState::RECORDING;
  RCLCPP_INFO(this->get_logger(), "Recording resumed");

  return true;
}

bool RecorderNode::stopRecording()
{
  if (recording_state_ == RecordingState::IDLE) {
    RCLCPP_WARN(this->get_logger(), "No active recording to stop");
    return false;
  }

  recording_state_ = RecordingState::STOPPING;

  RCLCPP_INFO(
    this->get_logger(),
    "Stopping recording. Total messages: %lu",
    messages_recorded_.load());

  recording_state_ = RecordingState::IDLE;
  messages_recorded_ = 0;

  return true;
}

RecordingState RecorderNode::getRecordingState() const
{
  return recording_state_.load();
}

std::vector<std::string> RecorderNode::getAvailableTopics() const
{
  std::vector<std::string> topics;
  for (const auto & [topic, type] : available_topics_) {
    topics.push_back(topic);
  }
  return topics;
}

void RecorderNode::onTimer()
{
  discoverTopics();
}

void RecorderNode::discoverTopics()
{
  auto topics_and_types = this->get_topic_names_and_types();

  for (const auto & [topic, types] : topics_and_types) {
    if (available_topics_.find(topic) == available_topics_.end()) {
      available_topics_[topic] = types.empty() ? "unknown" : types[0];
      RCLCPP_DEBUG(this->get_logger(), "Discovered topic: %s [%s]", topic.c_str(), available_topics_[topic].c_str());
    }
  }
}

}  // namespace rec_gui_intra_process

#include "rclcpp_components/register_node_macro.hpp"

RCLCPP_COMPONENTS_REGISTER_NODE(rec_gui_intra_process::RecorderNode)
