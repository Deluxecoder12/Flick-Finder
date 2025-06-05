# Grabs movie details from db
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
import os
import sqlite3

router = APIRouter()

load_dotenv()

@router.get("/{movie_id}")
def get_movie(movie_id: int):
    """
    Retrieve detailed information about a movie by ID.
    """
    try:
        # -- Connect to SQLite --
        conn = sqlite3.connect(os.getenv("DB_PATH", "data/movie_list.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, overview, genres, runtime_mins,
                   release_date, original_language, poster_path, popularity
            FROM movies
            WHERE id = ?
        """, (movie_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            raise HTTPException(status_code=404, detail="Movie not found")

        return {
            "id": row["id"],
            "title": row["title"],
            "overview": row["overview"],
            "genres": row["genres"],
            "runtime_mins": row["runtime_mins"],
            "release_date": row["release_date"],
            "original_language": row["original_language"],
            "poster_path": row["poster_path"],
            "popularity": row["popularity"]
        }

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")