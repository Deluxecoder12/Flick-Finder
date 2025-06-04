import sqlite3
from opensearchpy import OpenSearch, NotFoundError
import sys


# Connect to SQLite
conn = sqlite3.connect("data/movie_list.db")
cursor = conn.cursor()

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "admin"),
    use_ssl=False
)

# Define your OpenSearch index name
index_name = "movies"

# Create index if it doesn't exist
if not client.indices.exists(index=index_name):
    client.indices.create(index=index_name)

# Fetch all rows from the SQLite DB
cursor.execute("SELECT id, title, overview, genres, runtime_mins, release_date, original_language, poster_path, popularity, hash FROM movies")
rows = cursor.fetchall()

# Define OpenSearch fields
fields = [
    "id", "title", "overview", "genres", "runtime_mins",
    "release_date", "original_language", "poster_path", "popularity", "hash"
]

skipped = 0
updated = 0
spinner_sequence = ['/', '|', '-', '\\']
spinner_index = 0

for row in rows:
    doc = dict(zip(fields, row))
    try:
        doc["id"] = int(doc["id"])
        doc["runtime_mins"] = int(doc["runtime_mins"]) if doc["runtime_mins"] else 0
        doc["popularity"] = float(doc["popularity"]) if doc["popularity"] else 0.0
    except Exception as e:
        print(f"Skipping invalid data for ID {doc.get('id')}: {e}")
        continue

    try:
        existing = client.get(index=index_name, id=doc["id"])
        existing_hash = existing["_source"].get("hash")

        if existing_hash == doc["hash"]:
            skipped += 1
            continue  # skip unchanged
    except NotFoundError:
        pass  # Not in OpenSearch, so index it

    # Index into OpenSearch
    client.index(index=index_name, id=doc["id"], body=doc)
    updated += 1

    # Print progress
    i = rows.index(row) + 1
    if i % 50 == 0 or i == len(rows):
        spinner_char = spinner_sequence[spinner_index % len(spinner_sequence)]
        sys.stdout.write(f"\rIndexing... {spinner_char}")
        sys.stdout.flush()
        spinner_index += 1

sys.stdout.write("\rIndexing... Done!\n") # print doesn't work always well with \r..No idea why

print(f"{updated} documents updated or created.")
print(f"{skipped} documents skipped (no changes).")

# Close DB connection
conn.close()
