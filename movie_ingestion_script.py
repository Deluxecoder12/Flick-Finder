import tmdbsimple as tmdb
from dotenv import load_dotenv
import os
import sqlite3
import time

# Load API key and feed it to tmdb wrapper
load_dotenv()
tmdb.API_KEY = os.getenv("TMDB_API_KEY")

# Connect to SQLite DB
conn = sqlite3.connect(os.getenv("DB_PATH", "data/movie_list.db"))
cur = conn.cursor()

# Create table
cur.execute('''
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY, 
    title TEXT, 
    overview TEXT,
    genres TEXT,
    runtime_mins INTEGER,
    release_date TEXT,
    original_language TEXT,
    poster_path TEXT,
    popularity TEXT
)
''')

search = tmdb.Search()

# Loop over alphabet (a-z) to get a sample from each alphabet
for initial in range(ord('a'), ord('z') + 1):
    letter = chr(initial)
    for page in range(1, 3):  # Get 2 pages per letter (adjust as needed)
        response = search.movie(query=letter, page=page)
        for movie_data in search.results:
            try:
                movie = tmdb.Movies(movie_data['id'])
                details = movie.info()
                
                cur.execute('''
                INSERT OR IGNORE INTO movies (
                    id, title, overview, genres, runtime_mins, release_date,
                    original_language, poster_path, popularity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    details['id'],
                    details.get('title'),
                    details.get('overview'),
                    ', '.join([genre['name'] for genre in details.get('genres', [])]),
                    details.get('runtime'),
                    details.get('release_date'),
                    details.get('original_language'),
                    details.get('poster_path'),
                    str(details.get('popularity'))
                ))
                
                conn.commit()
                print(f"Processing movies starting with: {chr(initial)}, page {page}, title {details.get('title')}")
            except Exception as e:
                print("Error:", e)
                continue
        
        time.sleep(0.5)  # Avoid TMDb rate-limiting

conn.commit()
conn.close()
