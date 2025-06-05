# OpenSearch Querying
from fastapi import APIRouter, Query, HTTPException
from opensearchpy import OpenSearch
from dotenv import load_dotenv
import os

router = APIRouter()

load_dotenv()

# -- Connect to OpenSearch --
client = OpenSearch(
    hosts=[{"host": os.getenv("OPENSEARCH_HOST", "localhost"), "port": int(os.getenv("OPENSEARCH_PORT", 9200))}],
    http_auth=("admin", os.getenv("OPENSEARCH_PWD")),
    use_ssl=True,
    verify_certs=False,  # Please change these for production. I am not responsible for you getting hacked. Maybe I should add that to the README.
    ssl_show_warn=False
)

@router.get("/")
def search_movies(q: str = Query(..., min_length=1, description="Search query for movies")):
    """
    Search for movies based on a query string.
    """

    if not client:
        raise HTTPException(status_code=503, detail="Search engine not available")

    try:
        index_name = "movies"

        query = {
            "size": 20,
            "query": {
                "match": {
                    "title": q  # Dynamic user query
                }
            }
        }

        response = client.search(index=index_name, body=query)

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "id": source.get("id"),
                "title": source.get("title"),
                "overview": source.get("overview"),
                "poster_path": source.get("poster_path"),
                "popularity": source.get("popularity")
            })

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
