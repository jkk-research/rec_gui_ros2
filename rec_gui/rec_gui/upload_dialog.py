"""Popup window uploading a recording to Kleinkram with the klein CLI."""

import shlex
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk

NO_CHOICE = "-"
TEXT_SECONDARY = ("gray40", "#9A9A9A")
BG_INSET = ("#F9F9FA", "#1D1E1E")

# Project and mission picked last, offered again in the next popup
_last_choice: Dict[str, str] = {}


class KleinkramUploadDialog:
    """Pick a Kleinkram project and mission, then run klein upload."""

    def __init__(self, root: ctk.CTk, mcap_file: Path, font_mono: ctk.CTkFont):
        self.root = root
        self.mcap_file = mcap_file
        # Mission names of each project
        self.missions: Dict[str, List[str]] = {}

        self.window = ctk.CTkToplevel(root)
        self.window.title("Upload to Kleinkram")
        self.window.geometry("640x420")
        self.window.transient(root)
        # CTkToplevel can open behind the main window on Linux
        self.window.after(200, self.window.lift)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self.window, text="File", text_color=TEXT_SECONDARY, anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(16, 12), pady=(16, 4))
        ctk.CTkLabel(
            self.window, text=str(mcap_file), font=font_mono, anchor="w"
        ).grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=(16, 4))

        self.project_menu = self._dropdown(1, "Project", self._on_project_changed)
        self.mission_menu = self._dropdown(2, "Mission", lambda value: self._update_command())

        buttons = ctk.CTkFrame(self.window, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=8)
        self.btn_upload = ctk.CTkButton(
            buttons, text="Upload", width=110, state="disabled", command=self._on_upload
        )
        self.btn_upload.pack(side="left")
        self.progress = ctk.CTkProgressBar(buttons, mode="indeterminate", height=8)
        self.lbl_status = ctk.CTkLabel(buttons, text="Loading projects…", text_color=TEXT_SECONDARY)
        self.lbl_status.pack(side="left", padx=12)

        self.txt_output = ctk.CTkTextbox(
            self.window, font=font_mono, fg_color=BG_INSET, wrap="word", state="disabled"
        )
        self.txt_output.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=16, pady=(0, 16))

        self._run_in_background(self._load_missions, self._on_missions_loaded)

    def _dropdown(self, row: int, label: str, command) -> ctk.CTkOptionMenu:
        """Create a labelled, initially empty dropdown."""
        ctk.CTkLabel(
            self.window, text=label, text_color=TEXT_SECONDARY, anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=(16, 12), pady=4)
        menu = ctk.CTkOptionMenu(
            self.window, values=[NO_CHOICE], state="disabled",
            dynamic_resizing=False, command=command
        )
        menu.grid(row=row, column=1, sticky="ew", padx=(0, 16), pady=4)
        return menu

    def _run_in_background(self, work, done):
        """Run work() in a thread and pass its result (or exception) to done()."""
        def run():
            try:
                result = work()
            except Exception as e:
                result = e
            self.root.after(0, lambda: self.window.winfo_exists() and done(result))

        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def _load_missions() -> Dict[str, List[str]]:
        """Get the mission names of each project from the Kleinkram server."""
        import kleinkram

        missions: Dict[str, List[str]] = {
            project.name: [] for project in kleinkram.list_projects()
        }
        for mission in kleinkram.list_missions():
            missions.setdefault(mission.project_name, []).append(mission.name)
        return {project: sorted(names) for project, names in sorted(missions.items())}

    def _on_missions_loaded(self, result):
        """Fill the project dropdown once the missions arrived."""
        if isinstance(result, Exception):
            self.lbl_status.configure(text="Could not load projects")
            self._show_output(
                f"{type(result).__name__}: {result}\n\n"
                "Is the kleinkram package installed and are you logged in (klein login)?"
            )
            return
        if not result:
            self.lbl_status.configure(text="No projects found")
            return

        self.missions = result
        projects = list(result)
        self.project_menu.configure(values=projects, state="normal")
        project = _last_choice.get("project")
        self.project_menu.set(project if project in projects else projects[0])
        self._on_project_changed(self.project_menu.get())
        self.lbl_status.configure(text="")

    def _on_project_changed(self, project: str):
        """Offer the missions of the selected project."""
        missions = self.missions.get(project) or [NO_CHOICE]
        self.mission_menu.configure(
            values=missions, state="normal" if missions != [NO_CHOICE] else "disabled"
        )
        mission = _last_choice.get("mission")
        self.mission_menu.set(mission if mission in missions else missions[0])
        self._update_command()

    def _command(self) -> Optional[List[str]]:
        """The klein upload command for the selection, None without a mission."""
        mission = self.mission_menu.get()
        if mission == NO_CHOICE or not self.missions:
            return None
        return [
            "klein", "upload",
            "--project", self.project_menu.get(),
            "--mission", mission,
            str(self.mcap_file),
        ]

    def _update_command(self):
        """Show the upload command and enable Upload when there is a mission."""
        command = self._command()
        self.btn_upload.configure(state="normal" if command else "disabled")
        self._show_output(f"$ {shlex.join(command)}" if command else "Pick a mission.")

    def _show_output(self, text: str):
        """Replace the text in the output box."""
        self.txt_output.configure(state="normal")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("1.0", text)
        self.txt_output.configure(state="disabled")

    def _on_upload(self):
        """Run klein upload in the background."""
        command = self._command()
        if not command:
            return
        _last_choice.update(project=self.project_menu.get(), mission=self.mission_menu.get())

        for widget in (self.btn_upload, self.project_menu, self.mission_menu):
            widget.configure(state="disabled")
        self.lbl_status.configure(text="Uploading…")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.progress.start()

        def upload():
            return subprocess.run(command, capture_output=True, text=True)

        self._run_in_background(upload, lambda result: self._on_uploaded(command, result))

    def _on_uploaded(self, command: List[str], result):
        """Show how the upload went."""
        self.progress.stop()
        self.progress.pack_forget()
        for widget in (self.btn_upload, self.project_menu, self.mission_menu):
            widget.configure(state="normal")

        if isinstance(result, Exception):
            self.lbl_status.configure(text="Upload failed")
            self._show_output(f"$ {shlex.join(command)}\n\n{result}")
            return

        # Progress bars redraw their line with \r, keep only the final state
        output = "\n".join(
            line.split("\r")[-1] for line in (result.stdout + result.stderr).splitlines()
        )
        ok = result.returncode == 0
        self.lbl_status.configure(
            text="Uploaded" if ok else f"Upload failed (exit code {result.returncode})"
        )
        self._show_output(f"$ {shlex.join(command)}\n\n{output}")
