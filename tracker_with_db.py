import win32gui
import win32process
import psutil
import time
from datetime import datetime, timedelta
from collections import defaultdict
from database import Database

import logging

# Logging setup
logging.basicConfig(
    # logging.INFO - only INFO and above
    # logging.DEBUG - see everything
    # logging.WARNING - only warnings/errors
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s: %(message)s',
    datefmt = '%H:%M:%S'
)

def get_active_window_info():
    """
    Gets the name of active window/app
    Return: process name or None 
    """
    try:
        # grab foreground window
        window = win32gui.GetForegroundWindow()

        # if no valid window, skip
        if not window:
            return None

        # grab process ID of window
        _, pid = win32process.GetWindowThreadProcessId(window)

        # use psutil -> get process name fm PID
        process = psutil.Process(pid)
        process_name = process.name()

        return process_name
    
    except psutil.NoSuchProcess:
        # EXPECTED - window closed between checks
        logging.debug(f"Process disappeared (PID no longer exists)")
        return None
    except psutil.AccessDenied:
        # EXPECTED - system/protected process
        logging.debug(f"Access denied to process")
        return None
    except Exception as e:
        # UNEXPECTED!!!! needs fixing
        logging.error(f"Unexpected error getting window: {e}")
        return None
class ProjectTimeTracker:
    """
    Time tracker, saves sessions to db
    """
    # NEW but similar to old TimeTracker
    def __init__(self, db: Database, project_id: int, threshold_seconds = 30):
        # storing in database instead of memory
        self.db = db
        self.project_id = project_id
        self.threshold = threshold_seconds
        self.current_app = None
        self.session_start = None

        # get proj info from database
        self.project = db.get_project(project_id)
        if not self.project:
            raise ValueError(f"Projecct {project_id} not found!")
        
        logging.info(f"Tracking time for: {self.project['name']}")

    # NEW modified for DB
    def update(self, app_name):
        now = datetime.now()

        if app_name != self.current_app:
            if self.current_app and self.session_start:
                session_duration = (now - self.session_start).total_seconds()

                if session_duration >= self.threshold:
                    # change to safe to database
                    self.db.add_time_session(
                        project_id = self.project_id,
                        app_name = self.current_app,
                        start_time = self.session_start,
                        end_time = now,
                        duration = session_duration
                    )

                    # update logging msg
                    logging.info(
                        f"Saved {session_duration:.1f}s in {self.current_app}"
                        f" to project '{self.project['name']}"
                    )
                else:
                    # Log to ignore if less than threshold
                    logging.info(f"Ignored {session_duration:.1f}s...")
                
            self.current_app = app_name
            self.session_start = now

    def get_summary(self):
        """
        Get tracking summary from db
        
        :param self: -
        """
        # NEW: pullls from db
        time_data = self.db.get_project_time(self.project_id)
            
        summary = "\n" + "="*60 + "\n"
        summary += f"PROJECT: {self.project['name']}\n"
        summary += "="*60 + "\n"
        
        if time_data['total_seconds'] == 0:
            summary += "No time tracked yet!\n"
        else:
            # formatting total time
            total_seconds = time_data['total_seconds']
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)

            # showing appropriate units
            if hours > 0:
                summary += f"Total Time: {hours}h {minutes}m\n"
            elif minutes > 0:
                summary += f"Total Time: {minutes}m {seconds}s\n"
            else:
                summary += f"Total Time: {seconds}s\n"
            
            summary += "\nBreakdown by Application:\n"
            summary += "-"*60 + "\n"
            
            for app in time_data['app_breakdown']:
                app_seconds = app['duration']
                app_hours = int(app_seconds // 3600)
                app_minutes = int((app_seconds % 3600) // 60)
                app_secs = int(app_seconds % 60)
                
                if app_hours > 0:
                    summary += f"  {app['app_name']:30s} {app_hours}h {app_minutes}m\n"
                elif app_minutes > 0:
                    summary += f"  {app['app_name']:30s} {app_minutes}m {app_secs}s\n"
                else:
                    summary += f"  {app['app_name']:30s} {app_secs}s\n"
        
        summary += "="*60 + "\n"
        return summary

def select_or_create_project(db: Database):
    """
    Let user select existing project or create new one
    
    :param db: Database instance
    :return: Project ID
    """
    print("\n" + "="*60)
    print("PROJECT SELECTION")
    print("="*60)
    
    # Show existing projects
    projects = db.get_all_projects()
    
    if projects:
        print("\nExisting Projects:")
        for i, proj in enumerate(projects, 1):
            print(f"  {i}. {proj['name']} ({proj['status']})")
        print(f"  {len(projects) + 1}. Create new project")
    else:
        print("\nNo projects yet. Let's create one!")
        return create_new_project(db)
    
    # Get user choice
    while True:
        try:
            choice = input(f"\nSelect project (1-{len(projects) + 1}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(projects):
                selected = projects[choice_num - 1]
                print(f"\nSelected: {selected['name']}")
                return selected['id']
            elif choice_num == len(projects) + 1:
                return create_new_project(db)
            else:
                print(f"Please enter a number between 1 and {len(projects) + 1}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            exit(0)


def create_new_project(db: Database):
    """
    Create a new project
    
    :param db: Database instance
    :return: New project ID
    """
    print("\n" + "-"*60)
    print("CREATE NEW PROJECT")
    print("-"*60)
    
    name = input("Project name: ").strip()
    if not name:
        print("Name cannot be empty!")
        return create_new_project(db)
    
    print("\nProject status options:")
    print("  1. WIP (Work in Progress)")
    print("  2. Waitlist")
    print("  3. On Hold")
    
    status_map = {'1': 'WIP', '2': 'Waitlist', '3': 'On Hold'}
    status_choice = input("Select status (1-3, default: WIP): ").strip() or '1'
    status = status_map.get(status_choice, 'WIP')
    
    project_id = db.create_project(name, status)
    print(f"\n✓ Created project: {name} (ID: {project_id})")
    
    return project_id


def main():
    """
    Main tracking loop with database integration
    """
    print("="*60)
    print("ART TIME TRACKER - Database Edition")
    print("="*60)
    
    # Connect to database
    db = Database('time_tracker.db')
    
    try:
        # Select/create project
        project_id = select_or_create_project(db)
        
        print("\n" + "="*60)
        print("TRACKING STARTED")
        print("="*60)
        print("Minimum session: 30 seconds")
        print("Press Ctrl+C to stop and see report\n")
        
        # Start tracking
        tracker = ProjectTimeTracker(db, project_id, threshold_seconds=30)
        
        while True:
            active_app = get_active_window_info()
            if active_app:
                tracker.update(active_app)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("STOPPING TRACKER")
        print("="*60)
        print(tracker.get_summary())
        
    finally:
        db.close()
        print("\nDatabase connection closed.")
        print("Your time has been saved!")


if __name__ == "__main__":
    main()