/**
 * @file topic_listener.hpp
 * @brief Generic topic listener for subscribing to ROS 2 topics
 */

#ifndef REC_GUI_INTRA_PROCESS__TOPIC_LISTENER_HPP_
#define REC_GUI_INTRA_PROCESS__TOPIC_LISTENER_HPP_

#include <memory>
#include <string>
#include <functional>
#include <atomic>

#include "rclcpp/rclcpp.hpp"

namespace rec_gui_intra_process
{

class TopicListener
{
public:
  using MessageCallback = std::function<void(const std::string &, const std::shared_ptr<rclcpp::SerializedMessage> &)>;

  TopicListener(
    const std::string & topic_name,
    rclcpp::Node::SharedPtr node,
    MessageCallback callback);

  virtual ~TopicListener() = default;

  /**
   * Start listening to the topic
   */
  void start();

  /**
   * Stop listening to the topic
   */
  void stop();

  /**
   * Get the topic name
   */
  const std::string & getTopicName() const { return topic_name_; }

  /**
   * Get the message type
   */
  const std::string & getMessageType() const { return message_type_; }

  /**
   * Get the number of messages received
   */
  uint64_t getMessageCount() const { return message_count_; }

  /**
   * Check if listener is active
   */
  bool isActive() const { return active_; }

private:
  void messageCallback(const std::shared_ptr<rclcpp::SerializedMessage> msg);

  std::string topic_name_;
  std::string message_type_;
  rclcpp::Node::SharedPtr node_;
  MessageCallback callback_;
  std::shared_ptr<rclcpp::GenericSubscription> subscription_;
  std::atomic<bool> active_{false};
  std::atomic<uint64_t> message_count_{0};
};

}  // namespace rec_gui_intra_process

#endif  // REC_GUI_INTRA_PROCESS__TOPIC_LISTENER_HPP_
