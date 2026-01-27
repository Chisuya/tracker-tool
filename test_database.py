import os
from database import Database

def test_database():
    """
    Test database functionality
    """
    # Delete old test database if exists
    if os.path.exists('test_tracker.db'):
        os.remove('test_tracker.db')

    print("Testing database...")
    
    with Database('test_tracker.db') as db:
        # Create some test projects
        print("\n1. Creating projects...")
        yumii_id = db.create_project("Yumii Commission", "Finished")
        gamma_id = db.create_project("GammaAway Commission", "WIP")
        print(f"Created projects: {yumii_id}, {gamma_id}")
        
        # List all projects
        print("\n2. All projects:")
        projects = db.get_all_projects()
        for proj in projects:
            print(f"  - {proj['name']} ({proj['status']})")
        
        # Add some time sessions
        print("\n3. Adding time sessions...")
        from datetime import datetime, timedelta
        
        start = datetime.now() - timedelta(hours=2)
        end = start + timedelta(minutes=45)
        db.add_time_session(yumii_id, "Photoshop.exe", start, end, 2700)
        
        start = end
        end = start + timedelta(minutes=15)
        db.add_time_session(yumii_id, "PureRef.exe", start, end, 900)
        
        # Get project time
        print("\n4. Time for Yumii project:")
        time_data = db.get_project_time(yumii_id)
        print(f"  Total: {time_data['total_hours']:.2f} hours")
        print(f"  Breakdown:")
        for app in time_data['app_breakdown']:
            print(f"    - {app['app_name']}: {app['duration']/60:.1f} minutes")
    
    print("\nDatabase test complete!")

if __name__ == "__main__":
    test_database()