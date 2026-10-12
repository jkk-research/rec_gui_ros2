/**
 * @file topic_listener.cpp
 * @brief Implementation of generic topic listener
 */

#include "rec_gui_intra_process/topic_listener.hpp"

namespace rec_gui_intra_process
{

TopicListener::TopicListener(
  const std::string & topic_name,
  rclcpp::Node::SharedPtr node,
  MessageCallback callback)
: topic_name_(topic_name),
  node_(node),
  callback_(callback)
{
  // Get message type from topic
  auto topics_and_types = node_->get_topic_names_and_types();
  for (const auto & [topic, types] : topics_and_types) {
    if (topic == topic_name && !types.empty()) {
      message_type_ = types[0];
      break;
    }
  }
}

void TopicListener::start()
{
  if (active_) {
    return;
  }

  if (message_type_.empty()) {
    RCLCPP_ERROR(node_->get_logger(), "Cannot subscribe to topic %s: message type unknown", topic_name_.c_str());
    return;
  }

  auto default_qos = rclcpp::QoS(rclcpp::KeepLast(10));

  subscription_ = node_->create_generic_subscription(
    topic_name_,
    message_type_,
    default_qos,
    std::bind(&TopicListener::messageCallback, this, std::placeholders::_1));

  active_ = true;
  RCLCPP_INFO(node_->get_logger(), "Started listening to topic: %s (%s)", topic_name_.c_str(), message_type_.c_str());
}

void TopicListener::stop()
{
  if (!active_) {
    return;
  }

  subscription_.reset();
  active_ = false;
  RCLCPP_INFO(node_->get_logger(), "Stopped listening to topic: %s", topic_name_.c_str());
}

void TopicListener::messageCallback(const std::shared_ptr<rclcpp::SerializedMessage> msg)
{
  if (!active_) {
    return;
  }

  message_count_++;

  if (callback_) {
    callback_(topic_name_, msg);
  }
}

}  // namespace rec_gui_intra_process
