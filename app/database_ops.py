import sqlite3
class DatabaseOps:
    def __init__(self):
        self.conn = sqlite3.connect('searchs.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")

    def create_table(self):
        if self.cursor == None:
            print("Connection error")
            return 
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_res (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            link TEXT NOT NULL,
            image_url TEXT NOT NULL,
            category TEXT NOT NULL,
            user_info_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_info_id) REFERENCES user_info(id) ON DELETE CASCADE
        );
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_upload TEXT NOT NULL, 
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    def insert_user_upload(self, image_url, category):
        self.cursor.execute(
            "INSERT INTO user_info (image_upload, category) VALUES (?, ?)",
            (image_url, category,)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def insert_search_res(self, info, category, user_id, s3_url):
        self.cursor.execute(
            "INSERT INTO search_res (title, source, link, image_url, category, user_info_id) VALUES (?, ?, ?, ?, ?, ?)",
            (info.title, info.source, info.link, s3_url, category, user_id,)
        )
        self.conn.commit()

    def get_rem_times(self, curr):
        self.cursor.execute("SELECT COUNT(*) FROM user_info")
        used = self.cursor.fetchone()[0]
        real_curr = curr // 3 # Take 3 credits per visual search
        return real_curr - used

        