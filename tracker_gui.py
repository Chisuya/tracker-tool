import customtkinter as ctk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
from database import Database
from tracker_with_db import get_active_window_info, ProjectTimeTracker

# Set appearance
ctk.set_appearance_mode("light")  # Light mode for dreamy aesthetic
ctk.set_default_color_theme("blue")


class TimeTrackerGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("✨Time Tracker ✨")
        self.window.geometry("500x600")
        
        # Color palette
        self.colors = {
            'bg': '#FFE5F1',           # Soft pink background
            'card': '#FFF0F7',         # Light pink card
            'accent': '#FFB6D9',       # Bubble pink
            'text': '#8B5A7D',         # Muted purple text
            'button_active': '#FF99C9', # Active pink
            'button_hover': '#FFD6EA'   # Hover pink
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
        
        # Main card frame with rounded corners
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
            # Refresh dropdown
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
        # Get selected project
        selected = self.project_var.get()
        if not selected or selected == "No projects - create one!":
            messagebox.showwarning("No Project", "Please select or create a project first! 🎨")
            return
        
        # Extract project name from "Name (Status)" format
        project_name = selected.split(" (")[0]
        projects = self.db.get_all_projects()
        project = next((p for p in projects if p['name'] == project_name), None)
        
        if not project:
            messagebox.showerror("Error", "Project not found!")
            return
        
        self.current_project_id = project['id']
        self.tracker = ProjectTimeTracker(self.db, self.current_project_id, threshold_seconds=30)
        
        # Update UI
        self.is_tracking = True
        self.elapsed_seconds = 0
        self.track_button.configure(text="⏹ Stop Tracking", fg_color="#FF6B9D")
        self.status_label.configure(text=f"Tracking: {project_name} ✨")
        self.project_dropdown.configure(state="disabled")
        
        # Start tracking thread
        self.tracking_thread = threading.Thread(target=self.tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        # Start timer update
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
                # Update UI on main thread
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
            
            # Schedule next update
            self.window.after(1000, self.update_timer)
    
    def show_report(self):
        """Show time tracking report"""
        if not self.current_project_id:
            messagebox.showinfo("No Data", "Start tracking a project first! 🎨")
            return
        
        time_data = self.db.get_project_time(self.current_project_id)
        project = self.db.get_project(self.current_project_id)
        
        # Format report
        total_seconds = time_data['total_seconds']
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        report = f"📊 {project['name']}\n\n"
        
        # Format total time with seconds
        if hours > 0:
            report += f"Total: {hours}h {minutes}m\n\n"
        elif minutes > 0:
            report += f"Total: {minutes}m {seconds}s\n\n"
        else:
            report += f"Total: {seconds}s\n\n"
        
        report += "Breakdown:\n"
        for app in time_data['app_breakdown']:
            app_seconds = app['duration']
            app_hours = int(app_seconds // 3600)
            app_minutes = int((app_seconds % 3600) // 60)
            app_secs = int(app_seconds % 60)
            
            # Format each app time with seconds
            if app_hours > 0:
                report += f"• {app['app_name']}: {app_hours}h {app_minutes}m\n"
            elif app_minutes > 0:
                report += f"• {app['app_name']}: {app_minutes}m {app_secs}s\n"
            else:
                report += f"• {app['app_name']}: {app_secs}s\n"
        
        messagebox.showinfo("Time Report ✨", report)
    
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


if __name__ == "__main__":
    app = TimeTrackerGUI()
    app.run()