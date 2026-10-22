"""CustomTkinter GUI for the MCAP recording application."""

import os
import shlex
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path

import customtkinter as ctk

from .config import RecorderConfig, STORAGE_PRESETS
from .upload_dialog import KleinkramUploadDialog

# ── Color Palette (light, dark) ────────────────────────────────────────────
BG_INSET = ("#F9F9FA", "#1D1E1E")
TEXT_PRIMARY = ("gray10", "#DCE4EE")
TEXT_SECONDARY = ("gray40", "#9A9A9A")
BORDER_COLOR = ("#979DA2", "#565B5E")
HOVER_OUTLINE = ("gray78", "#3A3A3A")
ACCENT_BLUE = ("#3B8ED0", "#1F6AA5")
ACCENT_BLUE_HOVER = ("#36719F", "#144870")
ACCENT_BLUE_OFF = ("#9DC3E2", "#3A5F7D")
ACCENT_GREEN = ("#2CC985", "#2FA572")
ACCENT_RED = ("#D9443C", "#E5534B")
ACCENT_RED_HOVER = ("#B93630", "#C9443D")
ACCENT_ORANGE = "#FF9800"
STOP_RED = "#C0392B"
STOP_RED_HOVER = "#A93226"
STOP_OFF = ("gray70", "#4A4D50")

FONT_MONO = "DejaVu Sans Mono"
TOPIC_COLUMN_WIDTH = 260
NO_TOPICS_PLACEHOLDER = "<no topics selected>"
NO_OPTION = "-"
BYTES_PER_MB = 1024 * 1024


class RecordingState(Enum):
    """Enumeration of recording states."""
    IDLE = "idle"
    STARTING = "starting"
    RECORDING = "recording"
    STOPPING = "stopping"
    ERROR = "error"


class RecorderGUI:
    """CustomTkinter GUI for MCAP recording."""

    def __init__(self, root: ctk.CTk, config: RecorderConfig, ros_node=None):
        """Initialize the RecorderGUI."""
        self.root = root
        self.config = config
        self.ros_node = ros_node

        ctk.set_appearance_mode("dark")

        self.root.title("rec_gui - MCAP Recorder")
        self.root.geometry(
            f"{self.config.get('gui.window_width', 1100)}"
            f"x{self.config.get('gui.window_height', 760)}"
        )
        self.root.minsize(860, 600)

        self.recording_state = RecordingState.IDLE
        self.current_recording_start_time: Optional[datetime] = None
        self.available_topics: Dict[str, Dict] = {}
        self.selected_topics: set = set()
        self.topic_boxes: Dict[str, ctk.CTkCheckBox] = {}
        self.topic_vars: Dict[str, tk.BooleanVar] = {}
        self.topic_columns = 0
        self.active_command: Optional[str] = None
        self.last_output: Optional[Path] = None

        self.font_title = ctk.CTkFont(size=24, weight="bold")
        self.font_large = ctk.CTkFont(size=15, weight="bold")
        self.font_normal = ctk.CTkFont(size=14)
        self.font_small = ctk.CTkFont(size=12)
        self.font_duration = ctk.CTkFont(size=30, weight="bold")
        self.font_mono = ctk.CTkFont(family=FONT_MONO, size=12)
        self.font_topic = ctk.CTkFont(family=FONT_MONO, size=13)

        self._create_widgets()
        self._setup_callbacks()
        self._on_profile_changed()
        self._refresh_topics()
        self._start_gui_updates()

    # ─ Widget helpers ──────────────────────────────────────────────────────────
    def _filled_button(self, master, text: str, command, **kwargs) -> ctk.CTkButton:
        """Create a filled accent button."""
        return ctk.CTkButton(
            master,
            text=text,
            font=self.font_normal,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color=("white", "#DCE4EE"),
            command=command,
            **kwargs
        )

    def _outline_button(self, master, text: str, command, **kwargs) -> ctk.CTkButton:
        """Create an outlined secondary button."""
        return ctk.CTkButton(
            master,
            text=text,
            font=self.font_normal,
            fg_color="transparent",
            hover_color=HOVER_OUTLINE,
            border_width=2,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            command=command,
            **kwargs
        )

    def _create_widgets(self):
        """Create all GUI widgets."""
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._create_sidebar()

        content = ctk.CTkFrame(self.root, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._create_profile_card(content)
        self._create_topics_card(content)
        self._create_command_card(content)

    def _create_sidebar(self):
        """Create the sidebar with the recording controls."""
        # ─ Sidebar ─────────────────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self.root, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(9, weight=1)

        ctk.CTkLabel(
            sidebar,
            text="rec_gui",
            font=self.font_title,
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 17))

        self.btn_start = self._filled_button(
            sidebar, "Start recording", self._on_start,
            height=34,
            text_color_disabled=("gray95", "#9AA7B2")
        )
        self.btn_start.grid(row=1, column=0, sticky="ew", padx=20, pady=7)

        self.btn_stop = ctk.CTkButton(
            sidebar,
            text="Stop",
            font=self.font_normal,
            height=34,
            fg_color=STOP_OFF,
            hover_color=STOP_RED_HOVER,
            text_color="white",
            text_color_disabled=("gray45", "#8A8A8A"),
            state="disabled",
            command=self._on_stop
        )
        self.btn_stop.grid(row=2, column=0, sticky="ew", padx=20, pady=7)

        # Duration and recording state
        duration_box = ctk.CTkFrame(sidebar, fg_color=BG_INSET, corner_radius=6)
        duration_box.grid(row=3, column=0, sticky="ew", padx=20, pady=7)
        duration_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            duration_box,
            text="Duration",
            font=self.font_small,
            text_color=TEXT_SECONDARY,
            height=16,
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(12, 0), pady=(8, 0))

        self.status_indicator = ctk.CTkLabel(
            duration_box,
            text="● Ready",
            font=self.font_small,
            text_color=ACCENT_GREEN,
            height=16
        )
        self.status_indicator.grid(row=0, column=1, sticky="e", padx=(0, 12), pady=(8, 0))

        self.lbl_duration = ctk.CTkLabel(
            duration_box,
            text="0:00:00",
            font=self.font_duration,
            anchor="w"
        )
        self.lbl_duration.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))

        # Activity bar, only shown while recording
        self.progress = ctk.CTkProgressBar(duration_box, height=6, mode="indeterminate")
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        self.progress.grid_remove()

        # Recording tools (rosbag info, mcap info, foxglove)
        ctk.CTkLabel(
            sidebar,
            text="Last recording",
            font=self.font_small,
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).grid(row=4, column=0, sticky="ew", padx=20, pady=(15, 0))

        tools = ("Rosbag info", "MCAP info", "Open in Foxglove", "Upload to Kleinkram")
        for row, tool in enumerate(tools, 5):
            self._outline_button(
                sidebar, tool, lambda t=tool: self._on_tool_selected(t),
                height=34
            ).grid(row=row, column=0, sticky="ew", padx=20, pady=7)

        ctk.CTkLabel(
            sidebar, text="Appearance mode:", font=self.font_normal
        ).grid(row=10, column=0, sticky="ew", padx=20, pady=(7, 0))
        self.appearance_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["Dark", "Light", "System"],
            font=self.font_normal,
            height=32,
            command=self._on_appearance_changed
        )
        self.appearance_menu.grid(row=11, column=0, sticky="ew", padx=20, pady=7)

        ctk.CTkLabel(
            sidebar, text="UI scaling:", font=self.font_normal
        ).grid(row=12, column=0, sticky="ew", padx=20, pady=(7, 0))
        self.scaling_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["80%", "90%", "100%", "110%", "120%"],
            font=self.font_normal,
            height=32,
            command=self._on_scaling_changed
        )
        self.scaling_menu.set("100%")
        self.scaling_menu.grid(row=13, column=0, sticky="ew", padx=20, pady=(7, 24))

    def _create_profile_card(self, content):
        """Create the recording profile card: profile, output and record options."""
        # ─ Recording Profile ───────────────────────────────────────────────────
        card = ctk.CTkFrame(content, corner_radius=8)
        card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        card.grid_columnconfigure((0, 1), weight=1, uniform="profile")

        ctk.CTkLabel(
            card, text="Recording profile", font=self.font_large, anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 6))

        # Left: profile, output folder and daily sub-folder
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(20, 12), pady=(0, 16))
        left.grid_columnconfigure(0, weight=1)

        profiles = list((self.config.get_nested("recording", "profiles") or {}).keys())
        default_profile = self.config.get_nested("recording", "default_profile")
        if default_profile not in profiles:
            profiles.insert(0, default_profile)
        self.profile_var = tk.StringVar(value=default_profile)

        self.profile_menu = ctk.CTkOptionMenu(
            left,
            values=profiles,
            variable=self.profile_var,
            font=self.font_normal,
            height=32,
            dynamic_resizing=False,
            command=self._on_profile_changed
        )
        self.profile_menu.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 6))

        self.btn_save_profile = self._outline_button(
            left, "Save profile", self._save_profile,
            width=110,
            height=32
        )
        self.btn_save_profile.grid(row=0, column=1, pady=(0, 6))

        # Output directory (editable)
        ctk.CTkLabel(
            left,
            text="Output mcap folder",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        self.output_var = tk.StringVar(value=str(self.config.get_output_directory()))
        self.entry_output = ctk.CTkEntry(
            left,
            textvariable=self.output_var,
            font=ctk.CTkFont(size=13),
            height=30
        )
        self.entry_output.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(4, 6))

        self.btn_browse = self._filled_button(
            left, "Browse", self._edit_output_directory,
            width=110,
            height=30
        )
        self.btn_browse.grid(row=2, column=1, pady=(4, 6))

        # Daily sub-folder, e.g. <output>/2026_10_16_bosch01/
        self.daily_subfolder_var = tk.BooleanVar(value=False)
        self.chk_daily_subfolder = ctk.CTkCheckBox(
            left,
            text="Create daily sub-folder for mcaps",
            variable=self.daily_subfolder_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20,
            checkbox_height=20,
            command=self._on_daily_subfolder_toggled
        )
        self.chk_daily_subfolder.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # Right: ros2 bag record options and the recording name
        options_box = ctk.CTkFrame(card, fg_color=BG_INSET, corner_radius=6)
        options_box.grid(row=1, column=1, sticky="nsew", padx=(12, 20), pady=(0, 16))
        options_box.grid_rowconfigure((0, 5), weight=1)
        options_box.grid_columnconfigure(1, weight=1)

        labels = ("maxCache", "storagePreset", "output_prefix", "date_profile")
        for row, label in enumerate(labels, 1):
            ctk.CTkLabel(
                options_box,
                text=label,
                font=self.font_mono,
                text_color=TEXT_SECONDARY,
                height=18,
                anchor="w"
            ).grid(row=row, column=0, sticky="w", padx=(14, 12), pady=3)

        # Cache size is edited in MB, the configuration keeps bytes
        cache_box = ctk.CTkFrame(options_box, fg_color="transparent")
        cache_box.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=3)
        cache_box.grid_columnconfigure(0, weight=1)

        self.cache_size_var = tk.StringVar()
        self.entry_cache_size = ctk.CTkEntry(
            cache_box,
            textvariable=self.cache_size_var,
            font=self.font_mono,
            width=80,
            height=26
        )
        self.entry_cache_size.grid(row=0, column=0, sticky="ew")
        self.entry_cache_size.bind("<Return>", self._on_cache_size_edited)
        self.entry_cache_size.bind("<FocusOut>", self._on_cache_size_edited)
        ctk.CTkLabel(
            cache_box, text="MB", font=self.font_mono, height=18, anchor="e"
        ).grid(row=0, column=1, sticky="e", padx=(6, 0))

        # Dropdowns, the values are passed to ros2 bag record as they are
        self.option_vars: Dict[str, tk.StringVar] = {}
        self.option_menus: Dict[str, ctk.CTkOptionMenu] = {}
        for row, (key, values) in enumerate((("storage_preset", STORAGE_PRESETS),), 2):
            self.option_vars[key] = tk.StringVar()
            menu = ctk.CTkOptionMenu(
                options_box,
                values=[value or NO_OPTION for value in values],
                variable=self.option_vars[key],
                font=self.font_mono,
                dropdown_font=self.font_mono,
                height=26,
                dynamic_resizing=False,
                command=lambda value, key=key: self._on_option_selected(key, value)
            )
            menu.grid(row=row, column=1, sticky="ew", padx=(0, 14), pady=3)
            self.option_menus[key] = menu

        # Recording name: <output_prefix>_<date_profile>.mcap
        self.name_vars: Dict[str, tk.StringVar] = {}
        self.name_entries: Dict[str, ctk.CTkEntry] = {}
        for row, key in enumerate(("output_prefix", "date_profile"), 3):
            self.name_vars[key] = tk.StringVar()
            entry = ctk.CTkEntry(
                options_box,
                textvariable=self.name_vars[key],
                font=self.font_mono,
                height=26
            )
            entry.grid(row=row, column=1, sticky="ew", padx=(0, 14), pady=3)
            entry.bind("<KeyRelease>", lambda e, key=key: self._on_name_edited(key))
            self.name_entries[key] = entry

    def _create_topics_card(self, content):
        """Create the topic selection card."""
        # ─ Search and Topic List ───────────────────────────────────────────────
        card = ctk.CTkFrame(content, corner_radius=8)
        card.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            card, text="Topics to record", font=self.font_large, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 6))

        self.lbl_selected = ctk.CTkLabel(
            card,
            text="0 / 0 selected",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY
        )
        self.lbl_selected.grid(row=0, column=1, sticky="e", padx=20, pady=(16, 6))

        # Search box
        self.search_entry = ctk.CTkEntry(
            card,
            placeholder_text="Filter topics…",
            font=self.font_normal,
            height=32
        )
        self.search_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=6)

        # Topic checkboxes in a scrollable grid
        self.topics_frame = ctk.CTkScrollableFrame(
            card, fg_color=BG_INSET, corner_radius=6, height=120
        )
        self.topics_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=6)

        self.lbl_no_topics = ctk.CTkLabel(
            self.topics_frame,
            text="No topics found. Start your nodes, then press Refresh.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY
        )

        # Buttons below list
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(6, 16))

        self._filled_button(
            btn_frame, "Select all", self._select_all, width=90, height=30
        ).pack(side="left", padx=(0, 10))
        self._filled_button(
            btn_frame, "Select inverse", self._select_inverse, width=120, height=30
        ).pack(side="left", padx=(0, 10))
        self._outline_button(
            btn_frame, "Clear", self._clear_selection, width=70, height=30
        ).pack(side="left", padx=(0, 10))
        self._outline_button(
            btn_frame, "Refresh", self._refresh_topics, width=80, height=30
        ).pack(side="left")

    def _create_command_card(self, content):
        """Create the bottom card showing the record command."""
        # ─ Record Command ──────────────────────────────────────────────────────
        card = ctk.CTkFrame(content, corner_radius=8)
        card.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Record command", font=self.font_large, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(20, 12), pady=(12, 4))

        self.lbl_command_hint = ctk.CTkLabel(
            card,
            text="",
            font=self.font_small,
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self.lbl_command_hint.grid(row=0, column=1, sticky="ew", pady=(12, 4))

        self.btn_copy = self._outline_button(
            card, "Copy", self._copy_command, width=70, height=26
        )
        self.btn_copy.grid(row=0, column=2, padx=20, pady=(12, 4))

        self.txt_command = ctk.CTkTextbox(
            card,
            font=self.font_mono,
            fg_color=BG_INSET,
            corner_radius=6,
            height=74,
            wrap="word",
            state="disabled"
        )
        self.txt_command.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(4, 16))

    def _setup_callbacks(self):
        """Setup event callbacks."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.entry_output.bind("<Return>", self._on_output_edited)
        self.entry_output.bind("<FocusOut>", self._on_output_edited)
        self.topics_frame.bind("<Configure>", self._on_topics_resized)
        # CTkScrollableFrame only handles <MouseWheel>, X11 sends Button-4/5
        self.root.bind_all("<Button-4>", lambda e: self._on_mouse_wheel(e, -1), add="+")
        self.root.bind_all("<Button-5>", lambda e: self._on_mouse_wheel(e, 1), add="+")

    def _start_gui_updates(self):
        """Start periodic GUI updates."""
        self._update_display()

    def _update_display(self):
        """Update GUI display elements."""
        if (
            self.recording_state == RecordingState.RECORDING
            and self.current_recording_start_time
        ):
            elapsed = datetime.now() - self.current_recording_start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_duration.configure(text=f"{hours}:{minutes:02d}:{seconds:02d}")
            self._check_recording_alive()
        else:
            # Keep the timestamp of the previewed command current
            self._update_command()

        self.root.after(500, self._update_display)

    def _check_recording_alive(self):
        """Switch to the error state if ros2 bag record exited on its own."""
        if not (self.ros_node and hasattr(self.ros_node, "recording_exit_code")):
            return

        exit_code = self.ros_node.recording_exit_code()
        if exit_code is None:
            return

        self.ros_node.recording = False
        self.current_recording_start_time = None
        self._set_state(RecordingState.ERROR)
        messagebox.showerror(
            "Recording stopped",
            f"ros2 bag record exited with code {exit_code}.\n\n"
            f"{self.ros_node.recording_log_tail()}"
        )

    # ─ Topics ──────────────────────────────────────────────────────────────────
    def _visible_topics(self) -> List[str]:
        """Get the topics matching the search, in display order."""
        search_term = self.search_entry.get().lower()
        return [t for t in sorted(self.topic_boxes) if search_term in t.lower()]

    def _on_search(self, *args):
        """Filter topics based on search."""
        visible = self._visible_topics()
        columns = max(1, self.topic_columns)

        for box in self.topic_boxes.values():
            box.grid_forget()
        for i, topic in enumerate(visible):
            self.topic_boxes[topic].grid(
                row=i // columns, column=i % columns, sticky="w", padx=10, pady=6
            )

        if visible:
            self.lbl_no_topics.grid_forget()
        else:
            self.lbl_no_topics.grid(row=0, column=0, columnspan=columns, padx=10, pady=20)

    def _on_topics_resized(self, event=None):
        """Fit as many topic columns as the list is wide."""
        # A column has to hold the longest topic name next to its checkbox
        longest = max(self.topic_boxes, key=len, default="")
        column_width = max(TOPIC_COLUMN_WIDTH, self.font_topic.measure(longest) + 60)
        scaling = ctk.ScalingTracker.get_widget_scaling(self.topics_frame)
        columns = max(1, int(self.topics_frame.winfo_width() / (column_width * scaling)))
        if columns == self.topic_columns:
            return

        for column in range(max(columns, self.topic_columns)):
            self.topics_frame.grid_columnconfigure(
                column, weight=1 if column < columns else 0,
                uniform="topics" if column < columns else ""
            )
        self.topic_columns = columns
        self._on_search()

    def _on_mouse_wheel(self, event, direction: int):
        """Scroll the topic list with the mouse wheel on X11."""
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget and str(widget).startswith(str(self.topics_frame._parent_frame)):
            self.topics_frame._parent_canvas.yview_scroll(direction, "units")

    def _rebuild_topics(self):
        """Sync the checkboxes with the available and selected topics."""
        # Selected topics stay listed even while nobody publishes them
        topics = set(self.available_topics) | self.selected_topics
        locked = self.recording_state == RecordingState.RECORDING

        for topic in set(self.topic_boxes) - topics:
            self.topic_boxes.pop(topic).destroy()
            del self.topic_vars[topic]

        for topic in sorted(topics - set(self.topic_boxes)):
            var = tk.BooleanVar(value=topic in self.selected_topics)
            self.topic_vars[topic] = var
            self.topic_boxes[topic] = ctk.CTkCheckBox(
                self.topics_frame,
                text=topic,
                variable=var,
                font=self.font_topic,
                checkbox_width=20,
                checkbox_height=20,
                border_width=2,
                border_color=BORDER_COLOR,
                corner_radius=5,
                fg_color=ACCENT_BLUE,
                hover_color=ACCENT_BLUE_HOVER,
                state="disabled" if locked else "normal",
                command=lambda t=topic: self._on_topic_toggled(t)
            )

        for topic, box in self.topic_boxes.items():
            self.topic_vars[topic].set(topic in self.selected_topics)
            missing = topic not in self.available_topics
            box.configure(
                text_color=TEXT_SECONDARY if missing else TEXT_PRIMARY,
                border_width=3 if missing else 2,
                border_color=ACCENT_RED if missing else BORDER_COLOR,
                fg_color=ACCENT_RED if missing else ACCENT_BLUE,
                hover_color=ACCENT_RED_HOVER if missing else ACCENT_BLUE_HOVER
            )

        self._on_topics_resized()
        self._on_search()
        self._on_selection_changed()

    def _on_topic_toggled(self, topic: str):
        """Track a topic checkbox being toggled."""
        if self.topic_vars[topic].get():
            self.selected_topics.add(topic)
        else:
            self.selected_topics.discard(topic)
        self._on_selection_changed()

    def _set_visible_topics(self, selected):
        """Select or deselect the visible topics, selected(topic) decides."""
        if self.recording_state == RecordingState.RECORDING:
            return

        for topic in self._visible_topics():
            if selected(topic):
                self.selected_topics.add(topic)
            else:
                self.selected_topics.discard(topic)
            self.topic_vars[topic].set(topic in self.selected_topics)
        self._on_selection_changed()

    def _on_selection_changed(self):
        """Update everything that depends on the selected topics."""
        self.lbl_selected.configure(
            text=f"{len(self.selected_topics)} / {len(self.topic_boxes)} selected"
        )
        self._update_start_button()
        self._update_command()

    def _on_profile_changed(self, *args):
        """Auto-select topics and update settings when profile changes."""
        profile_name = self.profile_var.get()
        # Topics and record options come from the YAML, unsaved changes are dropped
        profile_data = self.config.reload_profile(profile_name)

        # Update output directory if profile specifies one
        if "output_directory" in profile_data:
            output_dir = profile_data["output_directory"]
            self.config.set("output.directory", output_dir)
            self.output_var.set(output_dir)
        self.daily_subfolder_var.set(self.config.get_daily_subfolder(profile_name))
        for key, value in self.config.get_name_options(profile_name).items():
            self.name_vars[key].set(value)

        record_options = self.config.get_record_options(profile_name)
        self.cache_size_var.set(f"{int(record_options['max_cache_size']) / BYTES_PER_MB:g}")
        for key, var in self.option_vars.items():
            var.set(str(record_options[key]) or NO_OPTION)

        # Auto-select topics from the profile
        self.selected_topics = set(profile_data.get("topics") or [])
        self._rebuild_topics()

    def _select_all(self):
        """Select all visible topics."""
        self._set_visible_topics(lambda topic: True)

    def _select_inverse(self):
        """Invert the selection of the visible topics."""
        self._set_visible_topics(lambda topic: topic not in self.selected_topics)

    def _clear_selection(self):
        """Clear all selections."""
        self._set_visible_topics(lambda topic: False)

    def _refresh_topics(self):
        """Refresh available topics."""
        if self.search_entry.get():
            self.search_entry.delete(0, "end")
        if self.ros_node and hasattr(self.ros_node, "get_available_topics"):
            try:
                topics = self.ros_node.get_available_topics()
                self.available_topics = {t: {"name": t} for t in topics}
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh topics: {e}")
        self._rebuild_topics()

    # ─ Record command ──────────────────────────────────────────────────────────
    def _update_command(self):
        """Show the ros2 bag record command at the bottom."""
        if self.recording_state == RecordingState.RECORDING and self.active_command:
            command = self.active_command
            hint = "running now"
        else:
            command = shlex.join(
                self.config.build_record_command(
                    [], self.profile_var.get(), self.output_var.get().strip() or None
                )
            )
            topics = sorted(self.selected_topics)
            command += " " + (shlex.join(topics) if topics else NO_TOPICS_PLACEHOLDER)
            hint = "what Start recording will run"

        self.lbl_command_hint.configure(text=hint)
        if command == self.txt_command.get("1.0", "end-1c"):
            return

        self.txt_command.configure(state="normal")
        self.txt_command.delete("1.0", "end")
        self.txt_command.insert("1.0", command)
        self.txt_command.configure(state="disabled")

    def _copy_command(self):
        """Copy the record command to the clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.txt_command.get("1.0", "end-1c"))
        self.btn_copy.configure(text="Copied")
        self.root.after(1500, lambda: self.btn_copy.configure(text="Copy"))

    # ─ Recording ───────────────────────────────────────────────────────────────
    def _on_start(self):
        """Start recording."""
        topics = sorted(self.selected_topics)
        if not topics:
            messagebox.showwarning("No Topics", "Please select at least one topic.")
            return

        self._on_output_edited()
        self._on_cache_size_edited()
        self._set_state(RecordingState.STARTING)

        if self.ros_node and hasattr(self.ros_node, "start_recording"):
            try:
                command = self.ros_node.start_recording(
                    topics, self.profile_var.get(), self.output_var.get().strip() or None
                )
                self.active_command = shlex.join(command)
                self.last_output = Path(command[command.index("-o") + 1])
                self.current_recording_start_time = datetime.now()
                self.lbl_duration.configure(text="0:00:00")
                self._set_state(RecordingState.RECORDING)
            except Exception as e:
                self._set_state(RecordingState.ERROR)
                messagebox.showerror("Error", f"Failed to start: {e}")

    def _on_stop(self):
        """Stop recording."""
        self._set_state(RecordingState.STOPPING)
        self.root.update_idletasks()
        if self.ros_node and hasattr(self.ros_node, "stop_recording"):
            try:
                self.ros_node.stop_recording()
                self._set_state(RecordingState.IDLE)
                self.current_recording_start_time = None
            except Exception as e:
                self._set_state(RecordingState.ERROR)
                messagebox.showerror("Error", f"Failed to stop: {e}")

    # ─ Last recording tools ────────────────────────────────────────────────────
    def _get_last_recording(self) -> Optional[Path]:
        """Find the most recent recording (a rosbag2 folder or a .mcap file)."""
        if self.last_output and self.last_output.exists():
            return self.last_output

        output_dir = Path(self.config.get_output_directory())
        if not output_dir.exists():
            return None

        # Directly in the output folder or in a daily sub-folder
        recordings = []
        for pattern in ("*", "*/*"):
            recordings += [p.parent for p in output_dir.glob(f"{pattern}/metadata.yaml")]
            recordings += [
                p for p in output_dir.glob(f"{pattern}.mcap")
                if not (p.parent / "metadata.yaml").exists()
            ]
        if not recordings:
            return None

        return max(recordings, key=lambda p: p.stat().st_mtime)

    @staticmethod
    def _get_mcap_file(recording: Path) -> Optional[Path]:
        """Get the newest .mcap file of a recording."""
        if recording.is_file():
            return recording
        files = sorted(recording.glob("*.mcap"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    def _on_tool_selected(self, tool: str):
        """Handle recording tools selection."""
        last_rec = self._get_last_recording()
        if not last_rec:
            messagebox.showwarning("No Recording", "No recording files found.")
            return

        mcap_file = self._get_mcap_file(last_rec)
        try:
            if tool == "Rosbag info":
                self._show_command_output(["ros2", "bag", "info", str(last_rec)])
            elif not mcap_file:
                messagebox.showwarning("No Recording", f"No .mcap file in {last_rec}")
            elif tool == "MCAP info":
                self._show_command_output(["mcap", "info", str(mcap_file)])
            elif tool == "Open in Foxglove":
                foxglove = shutil.which("foxglove-studio") or shutil.which("foxglove")
                if not foxglove:
                    messagebox.showwarning("Not Found", "Foxglove is not installed.")
                    return
                subprocess.Popen([foxglove, str(mcap_file)])
            elif tool == "Upload to Kleinkram":
                KleinkramUploadDialog(self.root, mcap_file, self.font_mono)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run tool: {e}")

    def _show_command_output(self, command: List[str]):
        """Run a command and show what it printed in a window."""
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)

        window = ctk.CTkToplevel(self.root)
        window.title(shlex.join(command[:3]))
        window.geometry("760x520")
        window.transient(self.root)

        text = ctk.CTkTextbox(window, font=self.font_mono, wrap="none")
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert("1.0", f"$ {shlex.join(command)}\n\n{result.stdout}{result.stderr}")
        text.configure(state="disabled")

    # ─ Profile and output ──────────────────────────────────────────────────────
    def _save_profile(self):
        """Save the selected topics, output folder and record options as a profile."""
        current = self.profile_var.get()
        name = ctk.CTkInputDialog(
            title="Save profile",
            text=f"Profile name (leave empty to overwrite '{current}'):"
        ).get_input()
        if name is None:
            return
        name = name.strip() or current

        self._on_output_edited()
        self._on_cache_size_edited()
        profile_data = dict(self.config.get_profile(name) or self.config.get_profile(current))
        profile_data["topics"] = sorted(self.selected_topics)
        profile_data["output_directory"] = self.output_var.get().strip()
        profile_data["daily_subfolder"] = self.daily_subfolder_var.get()
        profile_data.update(self.config.get_name_options(current))
        self.config.set(f"recording.profiles.{name}", profile_data)

        # The packaged YAML stays untouched, the user config is searched first
        save_path = Path.home() / ".rec_gui" / "rec_gui.yaml"
        self.config.save(save_path)

        self.profile_menu.configure(
            values=list(self.config.get_nested("recording", "profiles").keys())
        )
        self.profile_var.set(name)
        self._on_profile_changed()
        messagebox.showinfo("Profile saved", f"Profile '{name}' saved to:\n{save_path}")

    def _on_option_selected(self, key: str, value: str):
        """Apply a record option picked from a dropdown to the current profile."""
        value = "" if value == NO_OPTION else value
        self.config.set_record_option(self.profile_var.get(), key, value)
        self._update_command()

    def _on_cache_size_edited(self, event=None):
        """Apply the cache size typed into the entry, given in MB."""
        profile = self.profile_var.get()
        try:
            size = int(float(self.cache_size_var.get().replace(",", ".")) * BYTES_PER_MB)
            if size < 0:
                raise ValueError
            self.config.set_record_option(profile, "max_cache_size", size)
        except ValueError:
            # Not a size, show the one in use again
            size = int(self.config.get_record_options(profile)["max_cache_size"])
        self.cache_size_var.set(f"{size / BYTES_PER_MB:g}")
        self._update_command()

    def _on_name_edited(self, key: str):
        """Apply a typed output_prefix or date_profile to the current profile."""
        self.config.set_record_option(
            self.profile_var.get(), key, self.name_vars[key].get().strip()
        )
        self._update_command()

    def _on_daily_subfolder_toggled(self):
        """Apply the daily sub-folder checkbox to the current profile."""
        self.config.set_record_option(
            self.profile_var.get(), "daily_subfolder", self.daily_subfolder_var.get()
        )
        self._update_command()

    def _on_output_edited(self, event=None):
        """Apply the output folder typed into the entry."""
        output_dir = self.output_var.get().strip()
        if output_dir:
            self.config.set("output.directory", output_dir)
        self._update_command()

    def _edit_output_directory(self):
        """Edit the output directory."""
        current_dir = str(self.config.get_output_directory())
        new_dir = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=current_dir
        )

        if new_dir:
            try:
                # Create directory if it doesn't exist
                os.makedirs(new_dir, exist_ok=True)
                self.output_var.set(new_dir)
                self._on_output_edited()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set output directory: {e}")

    # ─ Appearance ──────────────────────────────────────────────────────────────
    def _on_appearance_changed(self, mode: str):
        """Switch between dark, light and system appearance."""
        ctk.set_appearance_mode(mode.lower())

    def _on_scaling_changed(self, scaling: str):
        """Scale the whole UI."""
        ctk.set_widget_scaling(int(scaling.rstrip("%")) / 100)

    def _on_close(self):
        """Handle window close."""
        if self.recording_state == RecordingState.RECORDING:
            if not messagebox.askyesno("Stop Recording", "Stop recording before closing?"):
                return
            self._on_stop()
        self.root.destroy()

    def _update_start_button(self):
        """Enable Start only when idle and at least one topic is selected."""
        busy = self.recording_state in (
            RecordingState.STARTING, RecordingState.RECORDING, RecordingState.STOPPING
        )
        enabled = not busy and bool(self.selected_topics)
        self.btn_start.configure(
            state="normal" if enabled else "disabled",
            fg_color=ACCENT_BLUE if enabled else ACCENT_BLUE_OFF
        )

    def _set_state(self, state: RecordingState):
        """Set recording state and update UI."""
        self.recording_state = state

        state_colors = {
            RecordingState.IDLE: ACCENT_GREEN,
            RecordingState.STARTING: ACCENT_ORANGE,
            RecordingState.RECORDING: ACCENT_RED,
            RecordingState.STOPPING: ACCENT_ORANGE,
            RecordingState.ERROR: ACCENT_RED,
        }

        state_text = {
            RecordingState.IDLE: "● Ready",
            RecordingState.STARTING: "● Starting...",
            RecordingState.RECORDING: "● Recording",
            RecordingState.STOPPING: "● Stopping...",
            RecordingState.ERROR: "● Error",
        }

        self.status_indicator.configure(
            text=state_text.get(state, "● Unknown"),
            text_color=state_colors.get(state, TEXT_SECONDARY)
        )

        recording = state == RecordingState.RECORDING
        if recording:
            self.btn_stop.configure(state="normal", fg_color=STOP_RED)
            self.progress.grid()
            self.progress.start()
        else:
            self.btn_stop.configure(state="disabled", fg_color=STOP_OFF)
            self.progress.stop()
            self.progress.grid_remove()

        # Profile, output, record options and topics are locked while recording
        locked = "disabled" if recording else "normal"
        for widget in (
            self.profile_menu, self.btn_save_profile, self.entry_output, self.btn_browse,
            self.chk_daily_subfolder, *self.name_entries.values(),
            self.entry_cache_size, *self.option_menus.values(),
            *self.topic_boxes.values()
        ):
            widget.configure(state=locked)

        self._update_start_button()
        self._update_command()

    def show(self):
        """Show the GUI and start the event loop."""
        self.root.mainloop()

    def update_topics(self, topics: List[str]):
        """Update available topics from external source."""
        self.available_topics = {t: {"name": t} for t in topics}
        self._rebuild_topics()
