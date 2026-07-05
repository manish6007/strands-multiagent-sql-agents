import os
import logging
from sqlalchemy import Column, Integer, Text, String, inspect, text
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector
from backend.app.database.connection import Base, engine

logger = logging.getLogger("app.database.pg_vector")

class KnowledgeBaseItem(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)  # glossary, kpi, schema, rule
    embedding = Column(Vector(1536), nullable=True)  # Titan Embedding size is 1536

def init_vector_db():
    """Create the vector extension and schema tables."""
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("Successfully enabled pgvector extension.")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension (might not have superuser privileges or postgres isn't running yet): {e}")
        
    try:
        # Check if table already exists, if not create it
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")

# Simple in-memory fallback store if database is offline or not configured
_memory_db = [
    {
        "title": "Active Customer",
        "content": "Active Customer = customer with at least one purchase within last 90 days",
        "category": "glossary",
        "embedding": [0.0] * 1536
    },
    {
        "title": "Churn Rate",
        "content": "Churn Rate = percentage of customers with no purchase in last 90 days",
        "category": "glossary",
        "embedding": [0.0] * 1536
    },
    {
        "title": "Revenue",
        "content": "Total Revenue = sum of quantity * price * (1 - discount)",
        "category": "kpi",
        "embedding": [0.0] * 1536
    }
]

def store_knowledge_item(db: Session, title: str, content: str, category: str, embedding: list[float] = None) -> bool:
    """Store knowledge item in database, fallback to memory if database fails."""
    try:
        item = KnowledgeBaseItem(
            title=title,
            content=content,
            category=category,
            embedding=embedding
        )
        db.add(item)
        db.commit()
        return True
    except Exception as e:
        logger.warning(f"Database write failed, writing to memory fallback: {e}")
        db.rollback()
        _memory_db.append({
            "title": title,
            "content": content,
            "category": category,
            "embedding": embedding
        })
        return True

def query_vector_db(db: Session, query_embedding: list[float], limit: int = 5) -> list[dict]:
    """Retrieve top_k matching documents using cosine distance in pgvector."""
    results = []
    try:
        # pgvector cosine distance operator is <=>
        # 1 - (embedding <=> query_embedding) is cosine similarity
        items = db.query(KnowledgeBaseItem).order_by(
            KnowledgeBaseItem.embedding.cosine_distance(query_embedding)
        ).limit(limit).all()
        
        for item in items:
            results.append({
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "score": 1.0  # Cosine distance ranking guarantees best order
            })
    except Exception as e:
        logger.warning(f"Database query failed, querying memory fallback: {e}")
        # Cosine similarity in-memory calculation
        if not query_embedding or not _memory_db:
            return [{k: v for k, v in item.items() if k != "embedding"} for item in _memory_db[:limit]]
            
        import numpy as np
        query_vec = np.array(query_embedding)
        scored_items = []
        for item in _memory_db:
            if item["embedding"] is not None:
                item_vec = np.array(item["embedding"])
                sim = np.dot(query_vec, item_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(item_vec) + 1e-9)
                scored_items.append((sim, item))
            else:
                scored_items.append((0.0, item))
                
        scored_items.sort(key=lambda x: x[0], reverse=True)
        for score, item in scored_items[:limit]:
            results.append({
                "title": item["title"],
                "content": item["content"],
                "category": item["category"],
                "score": float(score)
            })
            
    return results
