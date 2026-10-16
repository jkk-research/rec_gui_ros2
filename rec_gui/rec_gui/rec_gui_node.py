"""Main ROS 2 node for the MCAP recording GUI."""

import signal
import tkinter as tk
from pathlib import Path
from typing import List, Optional
import subprocess

import customtkinter as ctk

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
        self.recording_log: Optional[Path] = None
        self.last_output: Optional[Path] = None

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
        self,
        topics: List[str],
        profile: str = "default",
        output_dir: Optional[str] = None,
    ) -> List[str]:
        """
        Start recording specified topics.

        Args:
            topics: List of topic names to record
            profile: Recording profile name
            output_dir: Output directory, defaults to the configured one

        Returns:
            The ros2 bag record command that was started
        """
        if self.recording:
            raise RuntimeError("Recording already in progress")

        self.get_logger().info(
            f"Starting recording of {len(topics)} topics with profile '{profile}'"
        )

        cmd = self.config.build_record_command(topics, profile, output_dir)
        self.last_output = Path(cmd[cmd.index("-o") + 1])
        self.last_output.parent.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(" ".join(cmd))

        # ros2 bag record logs a lot, a pipe nobody reads would block it
        self.recording_log = self.config.get_log_directory() / "ros2_bag_record.log"
        with open(self.recording_log, "w") as log:
            self.recording_process = subprocess.Popen(
                cmd, stdout=log, stderr=subprocess.STDOUT
            )
        self.recording = True
        return cmd

    def recording_exit_code(self) -> Optional[int]:
        """Get the exit code of the recording process, None while it runs."""
        if self.recording_process is None:
            return None
        return self.recording_process.poll()

    def recording_log_tail(self, lines: int = 8) -> str:
        """Get the last lines ros2 bag record printed."""
        try:
            return "\n".join(self.recording_log.read_text().splitlines()[-lines:])
        except (AttributeError, OSError):
            return ""

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

        # SIGINT lets ros2 bag record close the MCAP file and write metadata
        if self.recording_process and self.recording_process.poll() is None:
            self.recording_process.send_signal(signal.SIGINT)
            try:
                self.recording_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.recording_process.terminate()
                try:
                    self.recording_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.recording_process.kill()
            self.get_logger().info("Recording stopped")
        else:
            self.get_logger().info("No active recording process to stop")

        if self.last_output:
            try:
                self.last_output = self._flatten_recording(self.last_output)
            except OSError as e:
                self.get_logger().error(f"Failed to move the .mcap out of {self.last_output}: {e}")

    def _flatten_recording(self, bag_dir: Path) -> Path:
        """
        Replace the rosbag2 folder <name>.mcap/ with the single .mcap file it holds.

        ros2 bag record always writes <name>.mcap/<name>.mcap_0.mcap and a
        metadata.yaml, rosbag2, mcap and Foxglove all read the .mcap alone.
        Folders with split or other files are kept as they are.
        """
        if not bag_dir.is_dir():
            return bag_dir
        files = [p for p in bag_dir.iterdir() if p.name != "metadata.yaml"]
        if len(files) != 1 or files[0].suffix != ".mcap":
            return bag_dir

        temporary = bag_dir.with_name(bag_dir.name + ".part")
        files[0].replace(temporary)
        (bag_dir / "metadata.yaml").unlink(missing_ok=True)
        bag_dir.rmdir()
        temporary.replace(bag_dir)
        self.get_logger().info(f"Recording saved to {bag_dir}")
        return bag_dir


def main(args=None):
    """Main entry point for the rec_gui node."""
    if rclpy is None:
        print("ERROR: rclpy is not available. Make sure ROS 2 is installed.")
        return

    rclpy.init(args=args)

    config = RecorderConfig()

    try:
        node = RecRecorderNode(config)

        root = ctk.CTk()
        gui = RecorderGUI(root, config, node)

        try:
            gui.show()
        except Exception as e:
            print(f"GUI error: {e}")
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass  # window already closed

    except Exception as e:
        print(f"Failed to create node: {e}")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
