import sqlite3
from typing import Optional, Tuple

class Database:
    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = '''
        CREATE TABLE IF NOT EXISTS mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id TEXT UNIQUE,
            page_id TEXT UNIQUE
        )
        '''
        self.connection.execute(query)
        self.connection.commit()

    def get_mapping(self, issue_id: str) -> Optional[Tuple[int, str, str]]:
        query = "SELECT * FROM mappings WHERE issue_id = ?"
        cursor = self.connection.execute(query, (issue_id,))
        return cursor.fetchone()

    def insert_mapping(self, issue_id: str, page_id: str):
        query = "INSERT INTO mappings (issue_id, page_id) VALUES (?, ?)"
        self.connection.execute(query, (issue_id, page_id))
        self.connection.commit()

    def update_mapping(self, issue_id: str, page_id: str):
        query = "UPDATE mappings SET page_id = ? WHERE issue_id = ?"
        self.connection.execute(query, (page_id, issue_id))
        self.connection.commit()
