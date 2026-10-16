""" rec_gui - MCAP Recording GUI for ROS 2."""

from .config import RecorderConfig
from .recorder_gui import RecorderGUI, RecordingState
from .rec_gui_node import RecRecorderNode, main

__version__ = "0.1.0"

__all__ = [
    "RecorderConfig",
    "RecorderGUI",
    "RecordingState",
    "RecRecorderNode",
    "main",
]
