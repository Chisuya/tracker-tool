import win32gui
import win32process
import psutil
import time
from datetime import datetime, timedelta
from collections import defaultdict

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
    
class TimeTracker:
    """
    Tracks time spent in different apps
    Only starts tracking after 30+ seconds in the window
    """
    def __init__(self, threshold_seconds = 30):
        self.threshold = threshold_seconds
        self.current_app = None
        self.session_start = None
        self.total_time = defaultdict(float) # in seconds
    
    def update(self, app_name):
        """
        Update tracking w/ current active application
        
        :param self: TimeTracker instance
        :param app_name: the current window
        """
        now = datetime.now()

        # If app changed
        if app_name != self.current_app:
            #save time fm prev app if 30+ seconds
            if self.current_app and self.session_start:
                session_duration = (now - self.session_start).total_seconds()

                if session_duration >= self.threshold:
                    self.total_time[self.current_app] += session_duration
                    print(f"Logged {session_duration:.1f}s in {self.current_app}")
                else:
                    print(f"Ignored {session_duration:.1f}s in {self.current_app} (below threshold)")

            #start new session
            self.current_app = app_name
            self.session_start = now

    def get_report(self):
        """
        Get formatted report of time tracked per app
        
        :param self: timetrack instance
        """
        if not self.total_time:
            return "No time tracked yet!"
        
        report = "\n" + "="*50 + "\n"
        report += "TIME TRACKING REPORT\n"
        report += "="*50 + "\n"

        # Sort time spent most -> least
        sorted_apps = sorted(self.total_time.items(), key = lambda x: x[1], reverse = True)

        for app, seconds in sorted_apps:
            minutes = seconds / 60
            hours = minutes / 60

            if hours >= 1:
                report += f"{app:30s} {hours:6.2f} hours\n"
            else:
                report += f"{app:30s} {minutes:6.2f} minutes\n"

        # Total time
        total_seconds = sum(self.total_time.values())
        total_hours = total_seconds / 3600
        report += "="*50 + "\n"
        report += f"{'TOTAL':30s} {total_hours:6.2f} hours\n"
        report += "="*50 + "\n"

        return report
    
def main():
    """
    Loop - checks for active window every 2 seconds
    """
    print("Starting application tracker...")
    print("Switch between applications to see the tracker in action!!")
    print("Press Ctrl+C to stop\n")

    tracker = TimeTracker(threshold_seconds = 30)

    try:
        while True:
            active_app = get_active_window_info()
            if active_app:
                tracker.update(active_app)

        time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nStopping tracker...")
        print(tracker.get_report())

    

if __name__ == "__main__":
    main()

