from fastapi import APIRouter, Query, HTTPException
from opensearchpy import OpenSearch
from dotenv import load_dotenv
import os

router = APIRouter()

load_dotenv()

@router.get("/")
def search_movies(
    q: str = Query(None, description="Search query for movie title"),
    genres: list[str] = Query(default=[], description="Filter by one or more genres"),
    languages: list[str] = Query(default=[], description="Filter by one or more original languages"),
    min_popularity: float = Query(None, description="Minimum popularity score"),
    max_popularity: float = Query(None, description="Maximum popularity score"),
    sort_by: str = Query("popularity", enum=["popularity", "release_date", "runtime_mins"], description="Sort field"),
    order: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """
    Search for movies using full-text, filters, and sorting.
    """
    client = OpenSearch(
        hosts=[{"host": os.getenv("OPENSEARCH_HOST", "localhost"), "port": int(os.getenv("OPENSEARCH_PORT", 9200))}],
        http_auth=("admin", os.getenv("OPENSEARCH_PWD")),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False  # Please change this for production. I am not responsible for your system getting hacked. Maybe I will add this on README.
    )

    if not client:
        raise HTTPException(status_code=503, detail="Search engine not available")

    try:
        index_name = "movies"
        must_clauses = []
        filter_clauses = []

        if q:
            must_clauses.append({
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "overview"]
                }
            })
        if genres:
            filter_clauses.append({
            "bool": {
                "should": [{"match": {"genres": genre}} for genre in genres],
                "minimum_should_match": 1
            }
        })
        if languages:
            filter_clauses.append({"terms": {"original_language.keyword": languages}})
        if min_popularity is not None or max_popularity is not None:
            range_query = {}
            if min_popularity is not None:
                range_query["gte"] = min_popularity
            if max_popularity is not None:
                range_query["lte"] = max_popularity
            filter_clauses.append({"range": {"popularity": range_query}})

        query = {
            "size": 20,
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

        response = client.search(index=index_name, body=query)

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "id": source.get("id"),
                "title": source.get("title"),
                "popularity": source.get("popularity"),
                "release_date": source.get("release_date"),
                "runtime_mins": source.get("runtime_mins"),
                "original_language": source.get("original_language"),
                "genres": source.get("genres")
            })

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
