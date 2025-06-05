# Starts the app
from fastapi import FastAPI
from app import search, movie

app = FastAPI(
    title="Flick Finder API",
    description="A FastAPI backend for movie discovery and details.",
    version="1.0.0"
)

# Include routes from search and movie
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(movie.router, prefix="/movie", tags=["Movie Info"])

# Root route
@app.get("/")
def read_root():
    return {"message": "Welcome to Flick Finder API"}
