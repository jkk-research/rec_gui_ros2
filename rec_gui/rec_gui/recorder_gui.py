"""Modern, minimalist GUI for MCAP recording application."""

import tkinter as tk
from tkinter import font as tkfont, messagebox, filedialog
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path
import os

from .config import RecorderConfig

# ── Modern Color Palette ───────────────────────────────────────────────────
BG_MAIN = "#FFFFFF"
BG_SECTION = "#F5F5F5"
TEXT_PRIMARY = "#212121"
TEXT_SECONDARY = "#757575"
BORDER_COLOR = "#BDBDBD"
ACCENT_GREEN = "#4CAF50"
ACCENT_RED = "#F44336"
ACCENT_BLUE = "#2196F3"


class RecordingState(Enum):
    """Enumeration of recording states."""
    IDLE = "idle"
    STARTING = "starting"
    RECORDING = "recording"
    STOPPING = "stopping"
    ERROR = "error"


class RecorderGUI:
    """Modern minimalist GUI for MCAP recording."""

    def __init__(self, root: tk.Tk, config: RecorderConfig, ros_node=None):
        """Initialize the RecorderGUI."""
        self.root = root
        self.config = config
        self.ros_node = ros_node

        self.root.title("REC GUI - MCAP Recorder")
        self.root.geometry("900x700")
        self.root.configure(bg=BG_MAIN)

        self.recording_state = RecordingState.IDLE
        self.current_recording_start_time: Optional[datetime] = None
        self.available_topics: Dict[str, Dict] = {}
        self.selected_topics: set = set()
        self.messages_recorded = 0

        # Modern fonts
        self.font_title = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.font_large = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.font_normal = tkfont.Font(family="Helvetica", size=10)
        self.font_small = tkfont.Font(family="Helvetica", size=9)

        self._create_widgets()
        self._setup_callbacks()
        self._start_gui_updates()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # ─ Header ──────────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=BG_MAIN, height=70)
        header.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            header,
            text="REC GUI",
            font=self.font_title,
            fg=TEXT_PRIMARY,
            bg=BG_MAIN
        ).pack(side="left")

        self.status_indicator = tk.Label(
            header,
            text="● Ready",
            font=self.font_normal,
            fg=ACCENT_GREEN,
            bg=BG_MAIN
        )
        self.status_indicator.pack(side="right")

        # Separator
        tk.Frame(self.root, bg=BORDER_COLOR, height=1).pack(fill="x")

        # ─ Main Content ────────────────────────────────────────────────────────
        content = tk.Frame(self.root, bg=BG_MAIN)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # ─ Controls Section ────────────────────────────────────────────────────
        ctrl_section = tk.Frame(content, bg=BG_MAIN)
        ctrl_section.pack(fill="x", pady=(0, 20))

        tk.Label(
            ctrl_section,
            text="Recording Controls",
            font=self.font_large,
            fg=TEXT_PRIMARY,
            bg=BG_MAIN
        ).pack(anchor="w", pady=(0, 10))

        # Control buttons frame
        buttons_frame = tk.Frame(ctrl_section, bg=BG_MAIN)
        buttons_frame.pack(fill="x")

        # Start button (large, green)
        self.btn_start = tk.Button(
            buttons_frame,
            text="▶ START RECORDING",
            font=self.font_large,
            bg=ACCENT_GREEN,
            fg="white",
            activebackground="#45a049",
            padx=20,
            pady=12,
            border=0,
            cursor="hand2",
            command=self._on_start
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        # Stop button (large, red)
        self.btn_stop = tk.Button(
            buttons_frame,
            text="⏹ STOP",
            font=self.font_large,
            bg=TEXT_SECONDARY,
            fg="white",
            activebackground="#757575",
            padx=20,
            pady=12,
            border=0,
            state="disabled",
            cursor="hand2",
            command=self._on_stop
        )
        self.btn_stop.pack(side="left", padx=5)

        # Recording tools dropdown (rosbag info, mcap info, foxglove)
        tools_var = tk.StringVar(value="Recording Tools")
        tools_menu = tk.OptionMenu(
            buttons_frame,
            tools_var,
            "rosbag info",
            "mcap info",
            "open in foxglove",
            command=lambda x: self._on_tool_selected(x, tools_var)
        )
        tools_menu.config(
            font=self.font_normal,
            bg=BG_SECTION,
            fg=TEXT_SECONDARY,
            padx=10,
            pady=6,
            activebackground=BORDER_COLOR,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=0,
            relief="solid",
            borderwidth=1
        )
        tools_menu["menu"].config(bg=BG_SECTION, fg=TEXT_PRIMARY, activebackground=BORDER_COLOR)
        tools_menu.pack(side="right", padx=(10, 0))

        # Settings button
        self.btn_settings = tk.Button(
            buttons_frame,
            text="⚙",
            font=self.font_large,
            bg=BG_SECTION,
            fg=TEXT_SECONDARY,
            activebackground=BORDER_COLOR,
            padx=12,
            pady=10,
            border=1,
            borderwidth=1,
            relief="solid",
            cursor="hand2",
            command=self._open_settings
        )
        self.btn_settings.pack(side="right", padx=(0, 5))

        # ─ Info Section ────────────────────────────────────────────────────────
        info_section = tk.Frame(content, bg=BG_SECTION, relief="solid", borderwidth=1)
        info_section.pack(fill="x", pady=(0, 20))

        info_inner = tk.Frame(info_section, bg=BG_SECTION)
        info_inner.pack(fill="x", padx=15, pady=12)

        # Duration and messages in one line
        tk.Label(
            info_inner,
            text="Duration:",
            font=self.font_small,
            fg=TEXT_SECONDARY,
            bg=BG_SECTION
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.lbl_duration = tk.Label(
            info_inner,
            text="00:00:00",
            font=self.font_large,
            fg=ACCENT_BLUE,
            bg=BG_SECTION
        )
        self.lbl_duration.grid(row=0, column=1, sticky="w", padx=(0, 30))

        tk.Label(
            info_inner,
            text="Messages:",
            font=self.font_small,
            fg=TEXT_SECONDARY,
            bg=BG_SECTION
        ).grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.lbl_messages = tk.Label(
            info_inner,
            text="0",
            font=self.font_large,
            fg=ACCENT_GREEN,
            bg=BG_SECTION
        )
        self.lbl_messages.grid(row=0, column=3, sticky="w")

        # Output directory (editable)
        output_row = tk.Frame(info_inner, bg=BG_SECTION)
        output_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        tk.Label(
            output_row,
            text="Output:",
            font=self.font_small,
            fg=TEXT_SECONDARY,
            bg=BG_SECTION
        ).pack(side="left", padx=(0, 10))

        self.lbl_output = tk.Label(
            output_row,
            text=str(self.config.get_output_directory()),
            font=self.font_small,
            fg=TEXT_PRIMARY,
            bg=BG_SECTION
        )
        self.lbl_output.pack(side="left", padx=(0, 10))

        tk.Button(
            output_row,
            text="✏ Edit",
            font=self.font_small,
            bg=BG_SECTION,
            fg=TEXT_SECONDARY,
            activebackground=BORDER_COLOR,
            padx=8,
            pady=2,
            border=0,
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            command=self._edit_output_directory
        ).pack(side="left", padx=(0, 5))

        # ─ Profile and Search Section ──────────────────────────────────────────
        profile_section = tk.Frame(content, bg=BG_MAIN)
        profile_section.pack(fill="x", pady=(0, 10))

        tk.Label(
            profile_section,
            text="Recording Profile",
            font=self.font_large,
            fg=TEXT_PRIMARY,
            bg=BG_MAIN
        ).pack(anchor="w", pady=(0, 8))

        profiles = list(self.config.get_nested("recording", "profiles").keys())
        self.profile_var = tk.StringVar(
            value=self.config.get_nested("recording", "default_profile")
        )
        # Track profile changes to auto-select topics
        self.profile_var.trace("w", self._on_profile_changed)

        profile_menu = tk.OptionMenu(profile_section, self.profile_var, *profiles)
        profile_menu.config(
            font=self.font_normal,
            bg=BG_SECTION,
            fg=TEXT_PRIMARY,
            padx=10,
            pady=6,
            activebackground=BORDER_COLOR,
            activeforeground=TEXT_PRIMARY,
            highlightthickness=0,
            relief="solid",
            borderwidth=1
        )
        profile_menu["menu"].config(bg=BG_SECTION, fg=TEXT_PRIMARY, activebackground=BORDER_COLOR)
        profile_menu.pack(anchor="w", fill="x")

        # ─ Search and Topic List ───────────────────────────────────────────────
        topics_section = tk.Frame(content, bg=BG_MAIN)
        topics_section.pack(fill="both", expand=True)

        tk.Label(
            topics_section,
            text="Topics to Record",
            font=self.font_large,
            fg=TEXT_PRIMARY,
            bg=BG_MAIN
        ).pack(anchor="w", pady=(0, 8))

        # Search box
        search_frame = tk.Frame(topics_section, bg=BG_MAIN)
        search_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            search_frame,
            text="🔍",
            font=self.font_normal,
            fg=TEXT_SECONDARY,
            bg=BG_MAIN
        ).pack(side="left", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=self.font_normal,
            fg=TEXT_PRIMARY,
            bg="white",
            insertbackground=TEXT_PRIMARY,
            relief="solid",
            borderwidth=1
        )
        search_entry.pack(fill="x", padx=(0, 5))

        # Topic listbox with scrollbar
        list_frame = tk.Frame(topics_section, bg=BG_MAIN)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.topics_list = tk.Listbox(
            list_frame,
            bg="white",
            fg=TEXT_PRIMARY,
            selectmode="multiple",
            yscrollcommand=scrollbar.set,
            font=self.font_normal,
            border=1,
            relief="solid",
            highlightthickness=0,
            activestyle="none"
        )
        self.topics_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.topics_list.yview)

        # Buttons below list
        btn_frame = tk.Frame(topics_section, bg=BG_MAIN)
        btn_frame.pack(fill="x", pady=(10, 0))

        tk.Button(
            btn_frame,
            text="Select All",
            font=self.font_small,
            bg=BG_SECTION,
            fg=TEXT_PRIMARY,
            activebackground=BORDER_COLOR,
            padx=10,
            pady=5,
            border=1,
            borderwidth=1,
            relief="solid",
            cursor="hand2",
            command=self._select_all
        ).pack(side="left", padx=(0, 5))

        tk.Button(
            btn_frame,
            text="Clear",
            font=self.font_small,
            bg=BG_SECTION,
            fg=TEXT_PRIMARY,
            activebackground=BORDER_COLOR,
            padx=10,
            pady=5,
            border=1,
            borderwidth=1,
            relief="solid",
            cursor="hand2",
            command=self._clear_selection
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Refresh",
            font=self.font_small,
            bg=BG_SECTION,
            fg=TEXT_PRIMARY,
            activebackground=BORDER_COLOR,
            padx=10,
            pady=5,
            border=1,
            borderwidth=1,
            relief="solid",
            cursor="hand2",
            command=self._refresh_topics
        ).pack(side="left", padx=5)

        # Initial refresh
        self._refresh_topics()

    def _setup_callbacks(self):
        """Setup event callbacks."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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
            self.lbl_duration.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.lbl_messages.config(text=str(self.messages_recorded))

        self.root.after(500, self._update_display)

    def _on_search(self, *args):
        """Filter topics based on search."""
        search_term = self.search_var.get().lower()
        self.topics_list.delete(0, "end")

        for topic in sorted(self.available_topics.keys()):
            if search_term in topic.lower():
                self.topics_list.insert("end", topic)

    def _on_profile_changed(self, *args):
        """Auto-select topics and update settings when profile changes."""
        profile_name = self.profile_var.get()
        profiles = self.config.get_nested("recording", "profiles")

        if profile_name in profiles:
            profile_data = profiles[profile_name]
            profile_topics = profile_data.get("topics", [])

            # Update output directory if profile specifies one
            if "output_directory" in profile_data:
                output_dir = profile_data["output_directory"]
                self.config.set("output.directory", output_dir)
                self.lbl_output.config(text=output_dir)

            # Clear current selection
            self.topics_list.selection_clear(0, "end")

            # Auto-select topics from the profile
            if profile_topics:
                for i in range(self.topics_list.size()):
                    topic = self.topics_list.get(i)
                    if topic in profile_topics:
                        self.topics_list.selection_set(i)

    def _select_all(self):
        """Select all visible topics."""
        self.topics_list.selection_set(0, "end")

    def _clear_selection(self):
        """Clear all selections."""
        self.topics_list.selection_clear(0, "end")

    def _refresh_topics(self):
        """Refresh available topics."""
        if self.ros_node and hasattr(self.ros_node, "get_available_topics"):
            try:
                topics = self.ros_node.get_available_topics()
                self.available_topics = {t: {"name": t} for t in topics}
                self._on_search()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh topics: {e}")

    def _on_start(self):
        """Start recording."""
        selected = self.topics_list.curselection()
        if not selected:
            messagebox.showwarning("No Topics", "Please select at least one topic.")
            return

        topics = [self.topics_list.get(i) for i in selected]
        self._set_state(RecordingState.STARTING)

        if self.ros_node and hasattr(self.ros_node, "start_recording"):
            try:
                self.ros_node.start_recording(topics, self.profile_var.get())
                self._set_state(RecordingState.RECORDING)
                self.current_recording_start_time = datetime.now()
                self.messages_recorded = 0
                self.lbl_duration.config(text="00:00:00")
            except Exception as e:
                self._set_state(RecordingState.ERROR)
                messagebox.showerror("Error", f"Failed to start: {e}")

    def _on_stop(self):
        """Stop recording."""
        self._set_state(RecordingState.STOPPING)
        if self.ros_node and hasattr(self.ros_node, "stop_recording"):
            try:
                self.ros_node.stop_recording()
                self._set_state(RecordingState.IDLE)
                self.current_recording_start_time = None
                self.lbl_duration.config(text="00:00:00")
                self.messages_recorded = 0
            except Exception as e:
                self._set_state(RecordingState.ERROR)
                messagebox.showerror("Error", f"Failed to stop: {e}")

    def _get_last_recording(self) -> Optional[Path]:
        """Find the most recently modified .mcap or .bag file."""
        output_dir = Path(self.config.get_output_directory())
        if not output_dir.exists():
            return None

        recordings = list(output_dir.glob("*.mcap")) + list(output_dir.glob("*.bag"))
        if not recordings:
            return None

        return max(recordings, key=lambda p: p.stat().st_mtime)

    def _on_tool_selected(self, tool: str, tools_var: tk.StringVar):
        """Handle recording tools selection."""
        tools_var.set("Recording Tools")  # Reset dropdown

        last_rec = self._get_last_recording()
        if not last_rec:
            messagebox.showwarning("No Recording", "No recording files found.")
            return

        try:
            if tool == "rosbag info":
                os.system(f"rosbag2 info '{last_rec}' &")
            elif tool == "mcap info":
                os.system(f"mcap info '{last_rec}' &")
            elif tool == "open in foxglove":
                os.system(f"foxglove '{last_rec}' &")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run tool: {e}")

    def _open_last_recording(self):
        """Open the last recording directory."""
        output_dir = self.config.get_output_directory()
        try:
            if output_dir.exists():
                os.startfile(output_dir) if os.name == 'nt' else os.system(f'open "{output_dir}"')
            else:
                messagebox.showwarning("Not Found", f"Directory not found: {output_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory: {e}")

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
                # Update config
                self.config.set("output.directory", new_dir)
                # Update label
                self.lbl_output.config(text=new_dir)
                # messagebox.showinfo("Success", f"Output directory changed to:\n{new_dir}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set output directory: {e}")

    def _open_settings(self):
        """Open settings dialog."""
        messagebox.showinfo("Settings", "Advanced settings will be implemented in the next version.")

    def _on_close(self):
        """Handle window close."""
        if self.recording_state == RecordingState.RECORDING:
            if not messagebox.askyesno("Stop Recording", "Stop recording before closing?"):
                return
            self._on_stop()
        self.root.destroy()

    def _set_state(self, state: RecordingState):
        """Set recording state and update UI."""
        self.recording_state = state

        state_colors = {
            RecordingState.IDLE: ACCENT_GREEN,
            RecordingState.STARTING: "#FF9800",
            RecordingState.RECORDING: ACCENT_RED,
            RecordingState.STOPPING: "#FF9800",
            RecordingState.ERROR: ACCENT_RED,
        }

        state_text = {
            RecordingState.IDLE: "● Ready",
            RecordingState.STARTING: "● Starting...",
            RecordingState.RECORDING: "● Recording",
            RecordingState.STOPPING: "● Stopping...",
            RecordingState.ERROR: "● Error",
        }

        self.status_indicator.config(
            text=state_text.get(state, "● Unknown"),
            fg=state_colors.get(state, TEXT_SECONDARY)
        )

        if state == RecordingState.RECORDING:
            self.btn_start.config(state="disabled", bg=TEXT_SECONDARY)
            self.btn_stop.config(state="normal", bg=ACCENT_RED)
        else:
            self.btn_start.config(state="normal", bg=ACCENT_GREEN)
            self.btn_stop.config(state="disabled", bg=TEXT_SECONDARY)

    def show(self):
        """Show the GUI and start the event loop."""
        self.root.mainloop()

    def update_topics(self, topics: List[str]):
        """Update available topics from external source."""
        self.available_topics = {t: {"name": t} for t in topics}
        self._on_search()
