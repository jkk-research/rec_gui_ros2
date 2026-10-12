/**
 * @file mcap_recorder_node_main.cpp
 * @brief Main entry point for the MCAP recorder node
 */

#include "rclcpp/rclcpp.hpp"
#include "rec_gui_intra_process/recorder_node.hpp"

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);

  rclcpp::NodeOptions options;
  options.use_intra_process_comms(true);

  auto node = std::make_shared<rec_gui_intra_process::RecorderNode>(options);

  rclcpp::spin(node);
  rclcpp::shutdown();

  return 0;
}
