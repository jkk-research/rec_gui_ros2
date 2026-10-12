"""Main ROS 2 node for the MCAP recording GUI."""

import sys
import tkinter as tk
from pathlib import Path
from typing import List, Optional
import subprocess
import threading

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy
except ImportError:
    rclpy = None
    Node = object

from .config import RecorderConfig
from .recorder_gui import RecorderGUI


class RecRecorderNode(Node):
    """ROS 2 node for MCAP recording with GUI."""

    def __init__(self, config: RecorderConfig):
        """
        Initialize the recording node.

        Args:
            config: RecorderConfig instance
        """
        node_name = config.get("ros2.node_name", "rec_gui")
        super().__init__(node_name)

        self.config = config
        self.recording = False
        self.available_topics: List[str] = []
        self.recording_process: Optional[subprocess.Popen] = None
        self.recording_thread: Optional[threading.Thread] = None

        self.declare_parameter(
            "config_file",
            str(Path(__file__).parent.parent / "resource" / "rec_gui.yaml"),
        )

        self.get_logger().info(f"Initializing {node_name} node")

    def get_available_topics(self) -> List[str]:
        """Get list of available ROS 2 topics."""
        try:
            topic_dict = self.get_topic_names_and_types()
            topics = [name for name, types in topic_dict]
            self.available_topics = sorted(topics)
            return self.available_topics
        except Exception as e:
            self.get_logger().error(f"Failed to get available topics: {e}")
            return []

    def start_recording(
        self, topics: List[str], profile: str = "default"
    ) -> None:
        """
        Start recording specified topics.

        Args:
            topics: List of topic names to record
            profile: Recording profile name
        """
        if self.recording:
            self.get_logger().warning("Recording already in progress")
            return

        self.recording = True
        self.get_logger().info(
            f"Starting recording of {len(topics)} topics with profile '{profile}'"
        )
        self.get_logger().info(f"Topics: {', '.join(topics)}")

        # Get profile configuration
        profiles = self.config.get_nested("recording", "profiles")
        profile_data = profiles.get(profile, {})

        # Get output settings
        output_dir = profile_data.get("output_directory") or str(self.config.get_output_directory())
        output_prefix = profile_data.get("output_prefix", "recording")
        compression = profile_data.get("compression", "zstd")

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Build ros2 bag record command
        cmd = [
            "ros2", "bag", "record",
            "-o", f"{output_dir}/{output_prefix}",
            "-c", compression,
            *topics,
        ]

        # Run recording in background thread
        def run_recording():
            try:
                self.recording_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.recording_process.wait()
            except Exception as e:
                self.get_logger().error(f"Recording error: {e}")
                self.recording = False

        self.recording_thread = threading.Thread(target=run_recording, daemon=True)
        self.recording_thread.start()

    def pause_recording(self) -> None:
        """Pause the current recording."""
        if not self.recording:
            self.get_logger().warning("No active recording to pause")
            return

        self.get_logger().info("Pausing recording")

    def stop_recording(self) -> None:
        """Stop the current recording."""
        if not self.recording:
            self.get_logger().warning("No active recording to stop")
            return

        self.recording = False

        # Terminate the recording process
        if self.recording_process and self.recording_process.poll() is None:
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.recording_process.kill()
            self.get_logger().info("Recording stopped")
        else:
            self.get_logger().info("No active recording process to stop")


def main(args=None):
    """Main entry point for the rec_gui node."""
    if rclpy is None:
        print("ERROR: rclpy is not available. Make sure ROS 2 is installed.")
        return

    rclpy.init(args=args)

    config = RecorderConfig()

    try:
        node = RecRecorderNode(config)

        root = tk.Tk()
        gui = RecorderGUI(root, config, node)

        try:
            gui.show()
        except Exception as e:
            print(f"GUI error: {e}")
        finally:
            root.destroy()

    except Exception as e:
        print(f"Failed to create node: {e}")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
