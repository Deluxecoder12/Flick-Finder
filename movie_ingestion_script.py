import tmdbsimple as tmdb
from dotenv import load_dotenv
import os
import sqlite3
import time
from datetime import datetime
import hashlib
import json

# Load API key
load_dotenv()
tmdb.API_KEY = os.getenv("TMDB_API_KEY")

# Connect to SQLite DB
conn = sqlite3.connect(os.getenv("DB_PATH", "data/movie_list.db"))
cur = conn.cursor()

# Create table with hash column if not exists
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
    popularity TEXT,
    hash TEXT
)
''')

# --- Utility functions ---
def safe_str(value):
    if value is None:
        return None  # keep None as None (optional: or return "" if you want no nulls)
    value_str = str(value).strip()
    return value_str if value_str else None  # return None for empty strings

def safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        # Validate date format strictly
        dt = datetime.strptime(value.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def compute_hash(movie_dict, fields):
    content = {k: movie_dict.get(k) for k in fields}
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

# Fields to hash
fields_to_hash = [
    "id", "title", "overview", "genres", "runtime_mins",
    "release_date", "original_language", "poster_path", "popularity"
]

movies_fetched = 0
movies_skipped = 0

search = tmdb.Search()

# Loop over alphabet (a-z)
for initial in range(ord('a'), ord('z') + 1):
    letter = chr(initial)
    for page in range(1, 3):  # Adjust # pages
        response = search.movie(query=letter, page=page)
        for movie_data in response['results']:
            movies_fetched += 1
            movie_id = movie_data['id']

            try:
                movie = tmdb.Movies(movie_id)
                details = movie.info()

                # Build movie dict
                movie_dict = {
                    "id": safe_int(details.get('id')),
                    "title": safe_str(details.get('title')),
                    "overview": safe_str(details.get('overview')),
                    "genres": safe_str(', '.join([genre['name'] for genre in details.get('genres', [])])),
                    "runtime_mins": safe_int(details.get('runtime')),
                    "release_date": safe_date(details.get('release_date')),
                    "original_language": safe_str(details.get('original_language')),
                    "poster_path": safe_str(details.get('poster_path')),
                    "popularity": str(safe_float(details.get('popularity')))
                }

                # Compute current hash
                new_hash = compute_hash(movie_dict, fields_to_hash)

                # Check existing hash in DB
                cur.execute("SELECT hash FROM movies WHERE id = ?", (movie_id,))
                row = cur.fetchone()

                if row and row[0] == new_hash:
                    movies_skipped += 1
                    print(f"Skipping movie {movie_id} — no changes detected.")
                    continue

                # Insert or replace with updated hash
                cur.execute('''
                    INSERT OR REPLACE INTO movies (
                        id, title, overview, genres, runtime_mins, release_date,
                        original_language, poster_path, popularity, hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    movie_dict["id"],
                    movie_dict["title"],
                    movie_dict["overview"],
                    movie_dict["genres"],
                    movie_dict["runtime_mins"],
                    movie_dict["release_date"],
                    movie_dict["original_language"],
                    movie_dict["poster_path"],
                    movie_dict["popularity"],
                    new_hash
                ))

                conn.commit()
                print(f"Processed: {movie_dict['title']}")

            except Exception as e:
                print(f"Error for ID {movie_id}: {e}")
                continue

        time.sleep(0.5)  # TMDb rate limiting

print(f"Movies fetched from TMDb: {movies_fetched}")
print(f"Movies skipped (no change in DB): {movies_skipped}")

cur.execute("SELECT COUNT(*) FROM movies")
total_in_db = cur.fetchone()[0]
print(f"Total movies currently in DB: {total_in_db}")

conn.commit()
conn.close()
