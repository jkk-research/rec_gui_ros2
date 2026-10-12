<h1 align="center">rec_gui</h1>

<p align="center">
  <b>MCAP Recording GUI for ROS 2</b><br>
  A simple, easy-to-use interface for recording and managing MCAP files in ROS 2.
</p>

<p align="center">
  <img alt="License: MIT OR Apache-2.0" src="https://img.shields.io/badge/license-MIT%20%2F%20Apache--2.0-3a3a3a?style=flat-square">
  <img alt="Status: early alpha" src="https://img.shields.io/badge/status-early%20alpha-d69e2e?style=flat-square">
  <img alt="ROS 2: Humble" src="https://img.shields.io/badge/ros2-humble-34aec5?style=flat-square">
  <img alt="ROS 2: Jazzy" src="https://img.shields.io/badge/ros2-jazzy-34aec5?style=flat-square">
</p>

# Installation

## Clone

It is assumed that your workspace is `~/ros2_ws`. 

```bash
cd ~/ros2_ws/src
```

```bash
git clone https://github.com/jkk-research/rec_gui
```

## Build

```bash
cd ~/ros2_ws
```

```bash
colcon build --packages-select rec_gui rec_gui_intra_process --cmake-args -DCMAKE_BUILD_TYPE=Release
```

# Run

```bash
source ~/ros2_ws/install/setup.bash
```

```bash
ros2 run rec_gui rec_gui
```

# Additinal install

Get the latest release tag of `mcap-cli` from GitHub:

```bash
TAG=$(curl -s https://api.github.com/repos/foxglove/mcap/releases \
  | grep -o '"tag_name": "releases/mcap-cli/[^"]*"' | head -1 | cut -d'"' -f4) && echo $TAG
```

```bash
curl -L -o mcap "https://github.com/foxglove/mcap/releases/download/${TAG}/mcap-linux-amd64"
```

```bash
chmod +x mcap
```

```bash
sudo mv mcap /usr/local/bin/
```

```bash
mcap info --help
```
