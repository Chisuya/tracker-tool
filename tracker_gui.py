import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
from database import Database
from tracker_with_db import get_active_window_info, ProjectTimeTracker
from icon_helper import get_app_icon, get_default_icon
import config

import os
import sys

if getattr(sys, 'frozen', False):
    # Get run script
    SCRIPT_DIR = sys._MEIPASS
else:
    # Run as .py script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(SCRIPT_DIR, "tracker_icon.ico")

# Set appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class TimeTrackerGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("✨Time Tracker ✨")
        self.window.geometry("500x600")

        # icon
        if os.path.exists(ICON_PATH):
            try:
                self.window.wm_iconbitmap(ICON_PATH)
            except:
                pass

        # Center window
        self.window.update_idletasks() # update window info
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 500) // 2 + 400 # center horizontally + 400 to right
        y = (screen_height - 600) // 2 # center vertically
        self.window.geometry(f"500x600+{x}+{y}")
        
        # Color palette
        self.colors = {
            'bg': '#FFE5F1',
            'card': '#FFF0F7',
            'accent': '#FFB6D9',
            'text': '#8B5A7D',
            'button_active': '#FF99C9',
            'button_hover': '#FFD6EA'
        }
        
        self.window.configure(fg_color=self.colors['bg'])
        
        # State
        self.db = Database('time_tracker.db')
        self.tracker = None
        self.is_tracking = False
        self.tracking_thread = None
        self.current_project_id = None
        self.elapsed_seconds = 0
        
        self.active_reports = []  # Track open report windows

        self.create_ui()
        
    def create_ui(self):
        """Create the UI"""
        
        # Title with emoji
        title = ctk.CTkLabel(
            self.window,
            text="✨ Time Tracker ✨",
            font=("Arial Rounded MT Bold", 32),
            text_color=self.colors['text']
        )
        title.pack(pady=20)
        
        # Main card frame
        self.card_frame = ctk.CTkFrame(
            self.window,
            fg_color=self.colors['card'],
            corner_radius=20,
            border_width=2,
            border_color=self.colors['accent']
        )
        self.card_frame.pack(pady=10, padx=30, fill="both", expand=True)
        
        # Project selection
        project_label = ctk.CTkLabel(
            self.card_frame,
            text="🎨 Select Project",
            font=("Arial Rounded MT Bold", 18),
            text_color=self.colors['text']
        )
        project_label.pack(pady=(20, 10))
        
        # Project dropdown
        self.project_var = ctk.StringVar()
        self.project_dropdown = ctk.CTkComboBox(
            self.card_frame,
            variable=self.project_var,
            values=self.get_project_names(),
            width=350,
            height=40,
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent'],
            button_color=self.colors['accent'],
            button_hover_color=self.colors['button_hover'],
            dropdown_hover_color=self.colors['button_hover'],
            font=("Arial", 14)
        )
        self.project_dropdown.pack(pady=10)
        
        # New project button
        new_project_btn = ctk.CTkButton(
            self.card_frame,
            text="➕ New Project",
            command=self.create_project_dialog,
            width=180,
            height=35,
            corner_radius=15,
            fg_color=self.colors['button_active'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        new_project_btn.pack(pady=10)
        
        # Timer display
        self.timer_label = ctk.CTkLabel(
            self.card_frame,
            text="00:00:00",
            font=("Arial Rounded MT Bold", 48),
            text_color=self.colors['text']
        )
        self.timer_label.pack(pady=20)
        
        # Current app label
        self.app_label = ctk.CTkLabel(
            self.card_frame,
            text="No app tracked",
            font=("Arial", 14),
            text_color=self.colors['text']
        )
        self.app_label.pack(pady=5)
        
        # Start/Stop button
        self.track_button = ctk.CTkButton(
            self.card_frame,
            text="▶ Start Tracking",
            command=self.toggle_tracking,
            width=250,
            height=50,
            corner_radius=25,
            fg_color=self.colors['button_active'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 18),
            text_color="white"
        )
        self.track_button.pack(pady=20)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.card_frame,
            text="Ready to track! 🌸",
            font=("Arial", 12),
            text_color=self.colors['text']
        )
        self.status_label.pack(pady=10)
        
        # Button container frame
        button_frame = ctk.CTkFrame(
            self.window,
            fg_color="transparent"
        )
        button_frame.pack(pady=10)

        # View report button
        report_btn = ctk.CTkButton(
            button_frame,
            text="📊 View Report",
            command=self.show_report,
            width=180,
            height=40,
            corner_radius=20,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        report_btn.pack(side="left", padx=5)

        # Settings button
        settings_btn = ctk.CTkButton(
            button_frame,
            text="⚙️ Settings",
            command=self.show_settings,
            width=180,
            height=40,
            corner_radius=20,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        settings_btn.pack(side="left", padx=5)

    def get_project_names(self):
        """Get list of project names for dropdown"""
        projects = self.db.get_all_projects()
        if not projects:
            return ["No projects - create one!"]
        return [f"{p['name']} ({p['status']})" for p in projects]
    
    def create_project_dialog(self):
        """Open dialog to create new project"""
        dialog = ctk.CTkInputDialog(
            text="Enter project name:",
            title="✨ New Project"
        )
        name = dialog.get_input()
        
        if name and name.strip():
            project_id = self.db.create_project(name.strip(), 'WIP')
            messagebox.showinfo("Success", f"Created project: {name} 🎨")
            self.project_dropdown.configure(values=self.get_project_names())
            self.project_var.set(f"{name} (WIP)")
    
    def toggle_tracking(self):
        """Start or stop tracking"""
        if not self.is_tracking:
            self.start_tracking()
        else:
            self.stop_tracking()
    
    def start_tracking(self):
        """Start time tracking"""
        selected = self.project_var.get()
        if not selected or selected == "No projects - create one!":
            messagebox.showwarning("No Project", "Please select or create a project first! 🎨")
            return
        
        project_name = selected.split(" (")[0]
        projects = self.db.get_all_projects()
        project = next((p for p in projects if p['name'] == project_name), None)
        
        if not project:
            messagebox.showerror("Error", "Project not found!")
            return
        
        self.current_project_id = project['id']
        self.tracker = ProjectTimeTracker(
        self.db, 
        self.current_project_id, 
        threshold_seconds=30,
        on_session_saved=self.on_session_saved
        )

        self.is_tracking = True
        self.elapsed_seconds = 0
        self.track_button.configure(text="⏹ Stop Tracking", fg_color="#FF6B9D")
        self.status_label.configure(text=f"Tracking: {project_name} ✨")
        self.project_dropdown.configure(state="disabled")
        
        self.tracking_thread = threading.Thread(target=self.tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        self.update_timer()
    
    def stop_tracking(self):
        """Stop time tracking"""
        self.is_tracking = False
        self.track_button.configure(text="▶ Start Tracking", fg_color=self.colors['button_active'])
        self.status_label.configure(text="Stopped 🌸")
        self.project_dropdown.configure(state="normal")
        self.app_label.configure(text="No app tracked")
        
        messagebox.showinfo("Stopped", "Time tracking stopped! Your data has been saved 💾")
    
    def on_session_saved(self, project_id, app_name, duration):
        """Called when session saved (from background thread!)"""
        self.window.after(0, self._notify_reports, project_id)
    
    def _notify_reports(self, project_id):
        """Notify report windows (runs in main thread)"""
        # Clean up closed windows
        self.active_reports = [r for r in self.active_reports if r.window.winfo_exists()]
        
        # Notify matching reports
        for report in self.active_reports:
            if report.project_id == project_id:
                report.trigger_refresh()
    
    def register_report(self, report_window):
        """Register a report window to receive updates"""
        self.active_reports.append(report_window)


    def tracking_loop(self):
        """Background tracking loop"""
        while self.is_tracking:
            active_app = get_active_window_info()
            if active_app and self.tracker:
                self.tracker.update(active_app)
                self.window.after(0, self.app_label.configure, {"text": f"Currently: {active_app}"})
            time.sleep(2)
    
    def update_timer(self):
        """Update timer display"""
        if self.is_tracking:
            self.elapsed_seconds += 1
            hours = self.elapsed_seconds // 3600
            minutes = (self.elapsed_seconds % 3600) // 60
            seconds = self.elapsed_seconds % 60
            
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.timer_label.configure(text=time_str)
            
            self.window.after(1000, self.update_timer)
    
    def show_report(self):
        """Show proj selection for reports"""
        selection = ProjectSelectionWindow(self.db, self.colors, gui=self)
        # delay so new window will be on top
        self.window.after(100, lambda: selection.window.lift())
        self.window.after(100, lambda: selection.window.focus_force())

    def show_settings(self):
        """Show settings window"""
        settings_window = SettingsWindow(self.colors, gui=self)
        # Small delay to ensure window stays on top
        self.window.after(100, lambda: settings_window.window.lift())
        self.window.after(100, lambda: settings_window.window.focus_force())
    
    def run(self):
        """Run the GUI"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_tracking:
            if messagebox.askokcancel("Quit", "Tracking is active. Stop and quit? 🌸"):
                self.is_tracking = False
                self.db.close()
                self.window.destroy()
        else:
            self.db.close()
            self.window.destroy()


class ReportWindow:
    """report window with editable table"""
    
    def __init__(self, db, project_id, colors, gui = None):
        self.db = db
        self.project_id = project_id
        self.colors = colors
        self.gui = gui
        
        self.window = ctk.CTkToplevel()
        self.window.title("📊 Time Report")
        self.window.geometry("700x600")

        if self.gui and self.gui.window.winfo_exists():
            parent_x = self.gui.window.winfo_x()
            parent_y = self.gui.window.winfo_y()
            self.window.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        self.window.configure(fg_color=colors['bg'])

        # Make window come to front
        self.window.lift()              # Bring to front
        self.window.focus_force()       # Force focus
        # self.window.grab_set()          # Make it modal (blocks parent until closed)
        
        self.project = db.get_project(project_id)
        self.time_data = db.get_project_time(project_id)

        self.needs_refresh = False
        
        self.create_ui()

        # Register with main GUI
        if self.gui:
            self.gui.register_report(self)
    
    def create_ui(self):
        """Create the report UI"""
        
        # Header
        header_frame = ctk.CTkFrame(
            self.window,
            fg_color=self.colors['card'],
            corner_radius=15
        )
        header_frame.pack(pady=20, padx=20, fill="x")
        
        project_label = ctk.CTkLabel(
            header_frame,
            text=f"📊 {self.project['name']}",
            font=("Arial Rounded MT Bold", 24),
            text_color=self.colors['text']
        )
        project_label.pack(pady=10)
        
        # Total time
        total_seconds = self.time_data['total_seconds']
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"
        
        total_label = ctk.CTkLabel(
            header_frame,
            text=f"Total Time: {time_str}",
            font=("Arial Rounded MT Bold", 18),
            text_color=self.colors['accent']
        )
        total_label.pack(pady=(0, 10))
        
        # Table frame
        table_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent']
        )
        table_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Table headers
        headers = ["Icon", "Application", "Time", "Actions"]
        header_widths = [60, 250, 150, 100]
        
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            label = ctk.CTkLabel(
                table_frame,
                text=header,
                font=("Arial Rounded MT Bold", 14),
                text_color=self.colors['text'],
                width=width
            )
            label.grid(row=0, column=i, padx=5, pady=10, sticky="w")
        
        # Separator
        separator = ctk.CTkFrame(
            table_frame,
            height=2,
            fg_color=self.colors['accent']
        )
        separator.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=5)
        
        # Table rows
        for idx, app in enumerate(self.time_data['app_breakdown']):
            row = idx + 2
            
            # Get app icon
            icon_img = get_app_icon(app['app_name'], size=32)
            if not icon_img:
                icon_img = get_default_icon(size=32)
            
            # Convert PIL Image to CTkImage (fixes HighDPI warning)
            ctk_image = ctk.CTkImage(
                light_image=icon_img,
                dark_image=icon_img,
                size=(32, 32)
            )
            
            # Icon
            icon_label = ctk.CTkLabel(
                table_frame,
                text="",
                image=ctk_image,
                width=60
            )
            icon_label.grid(row=row, column=0, padx=5, pady=5)

            # App name
            app_label = ctk.CTkLabel(
                table_frame,
                text=app['app_name'],
                font=("Arial", 12),
                text_color=self.colors['text'],
                width=250,
                anchor="w"
            )
            app_label.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            
            # Time (editable)
            app_seconds = app['duration']
            app_hours = int(app_seconds // 3600)
            app_minutes = int((app_seconds % 3600) // 60)
            app_secs = int(app_seconds % 60)
            
            if app_hours > 0:
                time_text = f"{app_hours}h {app_minutes}m"
            elif app_minutes > 0:
                time_text = f"{app_minutes}m {app_secs}s"
            else:
                time_text = f"{app_secs}s"
            
            time_entry = ctk.CTkEntry(
                table_frame,
                width=150,
                height=35,
                corner_radius=10,
                border_width=1,
                border_color=self.colors['accent'],
                fg_color="white",
                text_color=self.colors['text']
            )
            time_entry.insert(0, time_text)
            time_entry.grid(row=row, column=2, padx=5, pady=5)
            
            # Save button
            edit_btn = ctk.CTkButton(
                table_frame,
                text="💾",
                width=40,
                height=35,
                corner_radius=10,
                fg_color=self.colors['button_active'],
                hover_color=self.colors['button_hover'],
                command=lambda e=time_entry, a=app: self.save_time_edit(e, a)
            )
            edit_btn.grid(row=row, column=3, padx=5, pady=5)
        
        # Close button
        close_btn = ctk.CTkButton(
            self.window,
            text="✨ Close",
            command=self.window.destroy,
            width=200,
            height=40,
            corner_radius=20,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        close_btn.pack(pady=10)
    
    def trigger_refresh(self):
        """Called when new data saved (safe - main thread)"""
        if not self.needs_refresh:
            self.needs_refresh = True
            self.window.after(500, self.do_refresh)
    
    def do_refresh(self):
        """Actually refresh the display"""
        if not self.window.winfo_exists():
            return
        
        self.needs_refresh = False
        
        # Get fresh data
        self.time_data = self.db.get_project_time(self.project_id)
        self.project = self.db.get_project(self.project_id)
        
        # Clear and rebuild
        for widget in self.window.winfo_children():
            widget.destroy()
        
        self.create_ui()
        
        print(f"✨ Report refreshed!")
    
    def save_time_edit(self, entry, app_data):
        """Save edited time to database"""
        try:
            time_str = entry.get().strip()
            
            # Parse time
            total_seconds = 0
            
            if 'h' in time_str:
                parts = time_str.split('h')
                total_seconds += int(parts[0].strip()) * 3600
                if 'm' in parts[1]:
                    total_seconds += int(parts[1].replace('m', '').strip()) * 60
            elif 'm' in time_str:
                parts = time_str.split('m')
                total_seconds += int(parts[0].strip()) * 60
                if len(parts) > 1 and 's' in parts[1]:
                    total_seconds += int(parts[1].replace('s', '').strip())
            elif 's' in time_str:
                total_seconds = int(time_str.replace('s', '').strip())
            
            # Update database
            self.db.update_app_time_for_project(
                self.project_id,
                app_data['app_name'],
                total_seconds
            )
            
            # Refresh data
            self.time_data = self.db.get_project_time(self.project_id)
            
            messagebox.showinfo(
                "Saved! 💾",
                f"Updated {app_data['app_name']} to {time_str}"
            )
            
            # Optionally refresh the window
            self.window.destroy()
            ReportWindow(self.db, self.project_id, self.colors)
            
        except Exception as e:
            messagebox.showerror("Error", f"Invalid time format!\n\nUse: 2h 30m or 45m 30s or 120s\n\nError: {str(e)}")

class ProjectSelectionWindow:
    """Window to select which project to view report for"""
    
    def __init__(self, db, colors, gui = None):
        self.db = db
        self.colors = colors
        self.gui = gui
        
        self.window = ctk.CTkToplevel()
        self.window.title("📊 Select Project")
        self.window.geometry("500x600")

        # Position relative to parent window
        if self.gui and self.gui.window.winfo_exists():
            parent_x = self.gui.window.winfo_x()
            parent_y = self.gui.window.winfo_y()
            self.window.geometry(f"+{parent_x + 50}+{parent_y + 50}")

        self.window.configure(fg_color=colors['bg'])
        
         # Make window come to front
        self.window.lift()
        self.window.focus_force()
        # self.window.grab_set()  # Modal - must close this before using parent

        self.create_ui()
    
    def create_ui(self):
        """Create the project selection UI"""
        
        # Header
        title = ctk.CTkLabel(
            self.window,
            text="📊 View Project Reports",
            font=("Arial Rounded MT Bold", 28),
            text_color=self.colors['text']
        )
        title.pack(pady=20)
        
        subtitle = ctk.CTkLabel(
            self.window,
            text="Select a project to view its time report",
            font=("Arial", 14),
            text_color=self.colors['text']
        )
        subtitle.pack(pady=(0, 20))
        
        # Scrollable frame for projects
        projects_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent']
        )
        projects_frame.pack(pady=10, padx=30, fill="both", expand=True)
        
        # Get all projects
        projects = self.db.get_all_projects()
        
        if not projects:
            no_projects = ctk.CTkLabel(
                projects_frame,
                text="No projects yet! 🎨\n\nCreate a project to start tracking!",
                font=("Arial", 16),
                text_color=self.colors['text']
            )
            no_projects.pack(pady=50)
        else:
            for project in projects:
                self.create_project_card(projects_frame, project)
    
    def create_project_card(self, parent, project):
        """Create a card for each project"""
        
        # Get time data for this project
        time_data = self.db.get_project_time(project['id'])
        total_seconds = time_data['total_seconds']
        
        # Format time
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"
        
        # Card frame
        card = ctk.CTkFrame(
            parent,
            fg_color="white",
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent']
        )
        card.pack(pady=10, padx=10, fill="x")
        
        # Project info frame (left side)
        info_frame = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        # Project name
        name_label = ctk.CTkLabel(
            info_frame,
            text=project['name'],
            font=("Arial Rounded MT Bold", 18),
            text_color=self.colors['text'],
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        # Status badge
        status_colors = {
            'WIP': '#FFB6D9',
            'Finished': '#B6FFD9',
            'On Hold': '#FFD9B6',
            'Waitlist': '#D9B6FF'
        }
        
        status_frame = ctk.CTkFrame(
            info_frame,
            fg_color=status_colors.get(project['status'], '#FFB6D9'),
            corner_radius=10
        )
        status_frame.pack(anchor="w", pady=5)
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=f"  {project['status']}  ",
            font=("Arial", 12),
            text_color="white"
        )
        status_label.pack(padx=8, pady=2)
        
        # Time display
        time_label = ctk.CTkLabel(
            info_frame,
            text=f"⏱️ Total: {time_str}",
            font=("Arial", 14),
            text_color=self.colors['text'],
            anchor="w"
        )
        time_label.pack(anchor="w", pady=5)
        
        # Button container (right side)
        button_container = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        button_container.pack(side="right", padx=15, pady=10)

        # Edit button
        edit_btn = ctk.CTkButton(
            button_container,
            text="✏️",
            command=lambda p=project: self.edit_project(p['id'], p['name']),
            width=35,
            height=35,
            corner_radius=10,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial", 14),
            text_color="white"
        )
        edit_btn.pack(side="left", padx=5)

        # View button
        view_btn = ctk.CTkButton(
            button_container,
            text="📊 View Report",
            command=lambda p=project: self.open_report(p['id']),
            width=140,
            height=40,
            corner_radius=15,
            fg_color=self.colors['button_active'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        view_btn.pack(side="left", padx=5)
    
    def open_report(self, project_id):
        """Open report for selected project"""
        report = ReportWindow(self.db, project_id, self.colors, gui = self.gui)
        # delay so window is created, then at top
        self.window.after(100, lambda: report.window.lift())
        self.window.after(100, lambda: report.window.focus_force())

    def edit_project(self, project_id, current_name):
        """Edit project name"""
        dialog = ctk.CTkInputDialog(
            text=f"Edit project name:\n(Current: {current_name})",
            title="✏️ Edit Project"
        )
        new_name = dialog.get_input()
        
        if new_name and new_name.strip() and new_name.strip() != current_name:
            # Update in database
            self.db.update_project_name(project_id, new_name.strip())
            
            # Update main GUI dropdown if it exists
            if self.gui:
                self.gui.project_dropdown.configure(values=self.gui.get_project_names())
            
            messagebox.showinfo("Success! ✨", f"Project renamed to: {new_name.strip()}")
            
            # Refresh this window to show new name
            for widget in self.window.winfo_children():
                widget.destroy()
            self.create_ui()

class SettingsWindow:
    """Settings window for configuring the app"""
    
    def __init__(self, colors, gui=None):
        self.colors = colors
        self.gui = gui
        
        self.window = ctk.CTkToplevel()
        self.window.title("⚙️ Settings")
        self.window.geometry("500x400")
        
        # Position relative to parent
        if self.gui and self.gui.window.winfo_exists():
            parent_x = self.gui.window.winfo_x()
            parent_y = self.gui.window.winfo_y()
            self.window.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        self.window.configure(fg_color=colors['bg'])
        
        # Make window come to front
        self.window.lift()
        self.window.focus_force()
        
        self.create_ui()
    
    def create_ui(self):
        """Create the settings UI"""
        
        # Header
        title = ctk.CTkLabel(
            self.window,
            text="⚙️ Settings",
            font=("Arial Rounded MT Bold", 28),
            text_color=self.colors['text']
        )
        title.pack(pady=20)
        
        # Settings frame
        settings_frame = ctk.CTkFrame(
            self.window,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent']
        )
        settings_frame.pack(pady=10, padx=30, fill="both", expand=True)
        
        # Timezone setting
        timezone_label = ctk.CTkLabel(
            settings_frame,
            text="🌍 Timezone",
            font=("Arial Rounded MT Bold", 18),
            text_color=self.colors['text']
        )
        timezone_label.pack(pady=(20, 10))
        
        timezone_info = ctk.CTkLabel(
            settings_frame,
            text="This affects Google Calendar event times",
            font=("Arial", 12),
            text_color=self.colors['text']
        )
        timezone_info.pack(pady=(0, 10))
        
        # Timezone dropdown
        timezones = [
            'America/Los_Angeles',  # Pacific
            'America/Denver',       # Mountain
            'America/Chicago',      # Central
            'America/New_York',     # Eastern
            'Europe/London',        # UK
            'Europe/Paris',         # Central Europe
            'Europe/Berlin',        # Germany
            'Asia/Tokyo',           # Japan
            'Asia/Shanghai',        # China
            'Australia/Sydney',     # Australia
        ]
        
        # Friendly names
        timezone_display = {
            'America/Los_Angeles': 'Pacific Time (PT) - Los Angeles',
            'America/Denver': 'Mountain Time (MT) - Denver',
            'America/Chicago': 'Central Time (CT) - Chicago',
            'America/New_York': 'Eastern Time (ET) - New York',
            'Europe/London': 'GMT/BST - London',
            'Europe/Paris': 'CET/CEST - Paris',
            'Europe/Berlin': 'CET/CEST - Berlin',
            'Asia/Tokyo': 'JST - Tokyo',
            'Asia/Shanghai': 'CST - Shanghai',
            'Australia/Sydney': 'AEST/AEDT - Sydney',
        }
        
        # Get current timezone
        current_tz = config.get_timezone()
        current_display = timezone_display.get(current_tz, current_tz)
        
        self.timezone_var = ctk.StringVar(value=current_display)
        timezone_dropdown = ctk.CTkComboBox(
            settings_frame,
            variable=self.timezone_var,
            values=[timezone_display[tz] for tz in timezones],
            width=400,
            height=40,
            corner_radius=15,
            border_width=2,
            border_color=self.colors['accent'],
            button_color=self.colors['accent'],
            button_hover_color=self.colors['button_hover'],
            dropdown_hover_color=self.colors['button_hover'],
            font=("Arial", 14)
        )
        timezone_dropdown.pack(pady=10)
        
        # Store the mapping for saving
        self.display_to_tz = {v: k for k, v in timezone_display.items()}
        
        # Save button
        save_btn = ctk.CTkButton(
            settings_frame,
            text="💾 Save Settings",
            command=self.save_settings,
            width=200,
            height=45,
            corner_radius=20,
            fg_color=self.colors['button_active'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 16),
            text_color="white"
        )
        save_btn.pack(pady=30)
        
        # Close button
        close_btn = ctk.CTkButton(
            self.window,
            text="✨ Close",
            command=self.window.destroy,
            width=200,
            height=40,
            corner_radius=20,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        close_btn.pack(pady=10)
    
    def save_settings(self):
        """Save settings to config"""
        # Convert display name back to timezone ID
        display_name = self.timezone_var.get()
        timezone_id = self.display_to_tz.get(display_name)
        
        if timezone_id:
            config.set_timezone(timezone_id)
            messagebox.showinfo(
                "Saved! ✨",
                f"Timezone updated to {display_name}\n\nNew calendar events will use this timezone!"
            )
        else:
            messagebox.showerror("Error", "Invalid timezone selected")

if __name__ == "__main__":
    app = TimeTrackerGUI()
    app.run()