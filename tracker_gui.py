import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
from database import Database
from tracker_with_db import get_active_window_info, ProjectTimeTracker
from icon_helper import get_app_icon, get_default_icon

# Set appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class TimeTrackerGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("✨Time Tracker ✨")
        self.window.geometry("500x600")
        
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
        
        self.create_ui()
        
    def create_ui(self):
        """Create the dreamy UI"""
        
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
        
        # View report button
        report_btn = ctk.CTkButton(
            self.window,
            text="📊 View Report",
            command=self.show_report,
            width=200,
            height=40,
            corner_radius=20,
            fg_color=self.colors['accent'],
            hover_color=self.colors['button_hover'],
            font=("Arial Rounded MT Bold", 14),
            text_color="white"
        )
        report_btn.pack(pady=10)
    
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
        self.tracker = ProjectTimeTracker(self.db, self.current_project_id, threshold_seconds=30)
        
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
        ProjectSelectionWindow(self.db, self.colors)
    
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
    """Beautiful report window with editable table"""
    
    def __init__(self, db, project_id, colors):
        self.db = db
        self.project_id = project_id
        self.colors = colors
        
        self.window = ctk.CTkToplevel()
        self.window.title("📊 Time Report")
        self.window.geometry("700x600")
        self.window.configure(fg_color=colors['bg'])

        # Make window come to front
        self.window.lift()              # Bring to front
        self.window.focus_force()       # Force focus
        self.window.grab_set()          # Make it modal (blocks parent until closed)
        
        self.project = db.get_project(project_id)
        self.time_data = db.get_project_time(project_id)
        
        self.create_ui()
    
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
    
    def __init__(self, db, colors):
        self.db = db
        self.colors = colors
        
        self.window = ctk.CTkToplevel()
        self.window.title("📊 Select Project")
        self.window.geometry("500x600")
        self.window.configure(fg_color=colors['bg'])
        
         # Make window come to front
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()  # Modal - must close this before using parent

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
        
        # View button (right side)
        view_btn = ctk.CTkButton(
            card,
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
        view_btn.pack(side="right", padx=15, pady=10)
    
    def open_report(self, project_id):
        """Open report for selected project"""
        ReportWindow(self.db, project_id, self.colors)

if __name__ == "__main__":
    app = TimeTrackerGUI()
    app.run()