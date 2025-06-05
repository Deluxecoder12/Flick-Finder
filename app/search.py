from fastapi import APIRouter, Query, HTTPException
from opensearchpy import OpenSearch
from dotenv import load_dotenv
import os
import sqlite3

router = APIRouter()

load_dotenv()

def get_db_connection():
    """Helper function to get SQLite database connection"""
    conn = sqlite3.connect(os.getenv("DB_PATH", "data/movie_list.db"))
    conn.row_factory = sqlite3.Row
    return conn

def get_movie_details_from_sql(movie_ids):
    """Get detailed movie information from SQLite for given IDs"""
    if not movie_ids:
        return {}
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create placeholders for IN clause
            placeholders = ','.join('?' * len(movie_ids))
            
            cursor.execute(f"""
                SELECT id, title, overview, genres, runtime_mins,
                       release_date, original_language, poster_path, 
                       CAST(popularity AS REAL) as popularity
                FROM movies
                WHERE id IN ({placeholders})
            """, movie_ids)
            
            rows = cursor.fetchall()
            
            # Convert to dictionary with id as key for fast lookup
            movie_details = {}
            for row in rows:
                movie_details[row["id"]] = {
                    "id": row["id"],
                    "title": row["title"],
                    "overview": row["overview"],
                    "genres": row["genres"],
                    "runtime_mins": row["runtime_mins"],
                    "release_date": row["release_date"],
                    "original_language": row["original_language"],
                    "poster_path": row["poster_path"],
                    "popularity": float(row["popularity"]) if row["popularity"] else 0.0
                }
            
            return movie_details
            
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/")
def search_movies(
    q: str = Query(None, description="Search query for movie title"),
    genres: list[str] = Query(default=[], description="Filter by one or more genres"),
    languages: list[str] = Query(default=[], description="Filter by one or more original languages"),
    min_popularity: float = Query(None, description="Minimum popularity score"),
    max_popularity: float = Query(None, description="Maximum popularity score"),
    sort_by: str = Query("popularity", enum=["popularity", "release_date", "runtime_mins"], description="Sort field"),
    order: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of results per page (max 100)")
):
    """
    Search for movies using OpenSearch and enrich with SQLite details.
    Supports pagination with page and per_page parameters.
    """
    # Initialize OpenSearch client
    client = OpenSearch(
        hosts=[{"host": os.getenv("OPENSEARCH_HOST", "localhost"), "port": int(os.getenv("OPENSEARCH_PORT", 9200))}],
        http_auth=("admin", os.getenv("OPENSEARCH_PWD")),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False
    )

    if not client:
        raise HTTPException(status_code=503, detail="Search engine not available")

    try:
        index_name = "movies"
        must_clauses = []
        filter_clauses = []

        # Build OpenSearch query
        if q:
            must_clauses.append({"match": {"title": q}})
        if genres:
            filter_clauses.append({"terms": {"genres.keyword": genres}})
        if languages:
            filter_clauses.append({"terms": {"original_language.keyword": languages}})
        if min_popularity is not None or max_popularity is not None:
            range_query = {}
            if min_popularity is not None:
                range_query["gte"] = min_popularity
            if max_popularity is not None:
                range_query["lte"] = max_popularity
            filter_clauses.append({"range": {"popularity": range_query}})

        # Calculate pagination
        start_from = (page - 1) * per_page

        query = {
            "size": per_page,
            "from": start_from,
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "sort": [
                {sort_by: {"order": order}}
            ]
        }

        # Handle empty query case
        if not must_clauses and not filter_clauses:
            query["query"] = {"match_all": {}}

        # Execute OpenSearch query
        response = client.search(index=index_name, body=query)
        
        # Get total count for pagination info
        total_hits = response["hits"]["total"]["value"]
        total_pages = (total_hits + per_page - 1) // per_page  # Ceiling division

        # Extract movie IDs from OpenSearch results
        movie_ids = []
        opensearch_results = {}
        
        for hit in response["hits"]["hits"]:
            movie_id = hit["_source"].get("id")
            if movie_id:
                movie_ids.append(movie_id)
                # Store OpenSearch data (mainly for search ranking/sorting)
                opensearch_results[movie_id] = hit["_source"]

        # Get detailed information from SQLite
        movie_details = get_movie_details_from_sql(movie_ids)

        # If no movies found in SQLite, return empty results
        if not movie_details:
            return {
                "results": [],
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False,
                    "next_page": None,
                    "previous_page": None
                }
            }

        # Combine results, maintaining OpenSearch sort order
        final_results = []
        for movie_id in movie_ids:
            if movie_id in movie_details:
                # Use SQLite data as primary source (has all the details)
                movie_data = movie_details[movie_id]
                
                # You can add OpenSearch-specific data if needed
                # For example, search score:
                # movie_data["search_score"] = opensearch_results[movie_id].get("_score")
                
                final_results.append(movie_data)

        return {
            "results": final_results,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_results": total_hits,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "previous_page": page - 1 if page > 1 else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")