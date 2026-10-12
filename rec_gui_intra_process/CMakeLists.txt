cmake_minimum_required(VERSION 3.16)
project(rec_gui_intra_process)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosgraph_msgs REQUIRED)

# Include directories
include_directories(include)

# Source files
set(SOURCES
  src/recorder_node.cpp
  src/topic_listener.cpp
  src/mcap_writer.cpp
)

# Create a component library for composition
add_library(mcap_recorder_component SHARED ${SOURCES})
ament_target_dependencies(mcap_recorder_component
  rclcpp
  rclcpp_components
  std_msgs
  rosgraph_msgs
)
rclcpp_components_register_node(mcap_recorder_component
  PLUGIN "rec_gui_intra_process::RecorderNode"
  EXECUTABLE "mcap_recorder_node"
)

# Install targets
install(TARGETS
  mcap_recorder_node
  DESTINATION lib/${PROJECT_NAME}
)

install(TARGETS
  mcap_recorder_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

# Install headers
install(DIRECTORY include/
  DESTINATION include
)

# Install config files
install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Testing
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
