import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    """
    Database operations for time tracker
    """
    def __init__(self, db_path='time_tracker.db'):
        """
        Init database connection + make table if doesn't exist
        
        :param self: -
        :param db_path: path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """
        Establish database connection
        
        :param self: -
        """
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row # allow access columns by name instead of row[0]
        self.cursor = self.conn.cursor()

    def _create_tables(self):
        """
        Create tables if don't exist
        
        :param self: -
        """
        # Projects table
        # ? is placeholder, tuple prevent SQL injection attack
        # DO NOT USE f-strings OR % FORMATTING FOR SQL QUERIES!!!!
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'WIP',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Time sessions table
        # Foreign key links time_sessions to projects (data integrity)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                app_name TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                duration REAL NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        self.conn.commit()

    def create_project(self, name: str, status: str = 'WIP') -> int:
        """
        Create a new proj
        
        :param self: -
        :param name: Proj name

        :param status:  Proj status (WIP, Finished, On Hold, Waitlist)

        :return: Proj ID

        """
        self.cursor.execute(
            'INSERT INTO projects (name, status) VALUES (?, ?)',
            (name, status)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_all_projects(self) -> List[Dict]:
        """
        Get all projs
        
        :param self: -
        :return: List of projecct dictionaries

        """
        self.cursor.execute('SELECT * FROM projects ORDER by updated_at DESC')
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_project(self, project_id: int) -> Optional[Dict]:
        """
        Get a specific proj by ID
        
        :param self: -
        :param project_id: Project ID

        :return: Proj Dictionary or None if not found

        """
        self.cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_project_status(self, project_id: int, status: str):
        """
        Update proj status
        
        :param self: -
        :param project_id: Proj ID

        :param status: New status

        """
        self.cursor.execute(
            'UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (status, project_id)
        )
        self.conn.commit()

    def add_time_session(self, project_id: int, app_name: str, start_time: datetime, end_time: datetime, duration: float):
        """
        Add a time session to a proj
        
        :param self: -
        :param project_id: Proj ID
  
        :param app_name: Application name

        :param start_time: Session start time

        :param end_time: Session end time

        :param duration: Duration in seconds

        """
        self.cursor.execute(
            '''
            INSERT INTO time_sessions (project_id, app_name, start_time, end_time, duration)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (project_id, app_name, start_time, end_time, duration)
        )
        self.conn.commit()

    def get_project_time(self, project_id: int) -> Dict:
        """
        Get total time and breakdown by app for a proj
        
        :param self: -
        :param project_id: Proj ID

        :return: Dictionary with total time and app breakdown

        """
        # Total time
        self.cursor.execute(
            '''
            SELECT SUM(duration) as total_duration
            FROM time_sessions
            WHERE project_id = ?
            ''',
            (project_id,)
        )
        total = self.cursor.fetchone()['total_duration'] or 0

        # Per app breakdown
        self.cursor.execute(
            '''
            SELECT app_name, SUM(duration) as duration
            FROM time_sessions
            WHERE project_id = ?
            GROUP BY app_name
            ORDER BY duration DESC
            ''',
            (project_id,)
        )

        app_breakdown = [dict(row) for row in self.cursor.fetchall()]

        return {
            'total_seconds': total,
            'total_hours': total / 3600,
            'app_breakdown': app_breakdown
        }
    
    def update_app_time_for_project(self, project_id: int, app_name: str, new_duration: float):
        """
        Update total time for an app in a project
        This proportionally adjusts all sessions for that app
        
        :param project_id: Project ID
        :param app_name: Application name
        :param new_duration: New total duration in seconds
        """
        # Get current total for this app
        self.cursor.execute(
            '''
            SELECT SUM(duration) as current_total
            FROM time_sessions
            WHERE project_id = ? AND app_name = ?
            ''',
            (project_id, app_name)
        )
        
        result = self.cursor.fetchone()
        current_total = result['current_total'] if result and result['current_total'] else 0
        
        if current_total == 0:
            return  # Nothing to update
        
        # Calculate scaling factor
        scale_factor = new_duration / current_total
        
        # Update all sessions proportionally
        self.cursor.execute(
            '''
            UPDATE time_sessions
            SET duration = duration * ?
            WHERE project_id = ? AND app_name = ?
            ''',
            (scale_factor, project_id, app_name)
        )
        
        self.conn.commit()
    
    def close(self):
        """
        Close database connection
        
        :param self: -
        """
        if self.conn:
            self.conn.close()
    
    # Enter and exit for context manager, ensure database connection ALWAYS closed
    def __enter__(self):
        """
        Context manager enter
        
        :param self: Description
        """
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit
        
        :param self: -
        :param exc_type: -
        :param exc_value: -
        :param traceback: -
        """
        self.close()