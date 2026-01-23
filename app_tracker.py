import win32gui
import win32process
import psutil
import time

def get_active_window_info():
    """
    Gets the name of active window/app
    Return: process name or None 
    """
    try:
        # grab foreground window
        window = win32gui.GetForegroundWindow()

        # grab process ID of window
        _, pid = win32process.GetWindowThreadProcessId(window)

        # use psutil -> get process name fm PID
        process = psutil.Process(pid)
        process_name = process.name()

        return process_name
    
    except Exception as e:
        print(f"Error: Cannot get active window: {e}")
        return None
    
def main():
    """
    Loop - checks for active window every 2 seconds
    """
    print("Starting application tracker...")
    print("Switch between applications to see the tracker in action!!")
    print("Press Ctrl+C to stop\n")

    while True:
        active_app = get_active_window_info()
        if active_app:
            print(f"Active application: {active_app}")

        time.sleep(2)

if __name__ == "__main__":
    main()

