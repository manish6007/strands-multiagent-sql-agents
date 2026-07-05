import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.router import api_router
from backend.app.database.pg_vector import init_vector_db

logger = logging.getLogger("app.main")

app = FastAPI(
    title="Text-to-SQL Analytics Multi-Agent API",
    description="Enterprise Analytics Assistant utilizing Strands Agents, pgvector RAG context, and Amazon Athena database integration.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set CORS middleware settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup database initialization
@app.on_event("startup")
def on_startup():
    logger.info("Application starting up... Initializing components.")
    # Initialize pgvector database schema
    init_vector_db()
    logger.info("Database schemas ready. Ingestion pipeline is accessible.")

# Include the main routing layer
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
