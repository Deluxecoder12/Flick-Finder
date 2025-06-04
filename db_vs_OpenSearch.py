"""
    SQLite will be much faster for a smaller dataset.
"""

import sqlite3
from opensearchpy import OpenSearch
import time

# -- CONFIG --
DB_PATH = "data/movie_list.db"
INDEX_NAME = "movies"
SEARCH_TERM = "Batman"

# -- Connect to SQLite --
sqlite_conn = sqlite3.connect(DB_PATH)
sqlite_cursor = sqlite_conn.cursor()

# -- Connect to OpenSearch --
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "admin"),
    use_ssl=False
)

# -- Search SQLite --
start_sql = time.time()
sqlite_cursor.execute("SELECT title FROM movies WHERE title LIKE ?", ('%' + SEARCH_TERM + '%',))
sqlite_results = sqlite_cursor.fetchall()
end_sql = time.time()

# -- Search OpenSearch --
query = {
    "query": {
        "match": {
            "title": SEARCH_TERM
        }
    }
}

start_os = time.time()
response = client.search(index=INDEX_NAME, body=query)
opensearch_results = [(hit["_source"]["title"], hit["_score"]) for hit in response["hits"]["hits"]]
end_os = time.time()

# -- Print results summary --
print(f"🔎 Search term: '{SEARCH_TERM}'")
print("\nSQLite Results:")
for r in sqlite_results:
    print(" -", r[0])
print(f"\nSQLite search time: {end_sql - start_sql:.4f} seconds")

print("\nOpenSearch Results:")
for title, score in opensearch_results:
    print(f" - {title} (score: {score:.2f})")
print(f"\nOpenSearch search time: {end_os - start_os:.4f} seconds")

# -- Cleanup --
sqlite_conn.close()
