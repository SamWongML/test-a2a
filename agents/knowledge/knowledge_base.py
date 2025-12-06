"""LanceDB-based knowledge base for storing and retrieving research."""

import os
from datetime import datetime
from typing import Any

import google.generativeai as genai
import lancedb
from lancedb.pydantic import LanceModel, Vector
from pydantic import Field


class KnowledgeEntry(LanceModel):
    """A knowledge entry stored in LanceDB."""

    id: str = Field(description="Unique identifier")
    query: str = Field(description="Original query")
    content: str = Field(description="Research content/answer")
    source_agent: str = Field(description="Agent that produced this")
    created_at: str = Field(description="Timestamp")
    topics: str = Field(default="", description="Comma-separated topics")
    vector: Vector(768) = Field(description="Embedding vector")  # Gemini embedding size


class KnowledgeBase:
    """Vector database for storing and retrieving knowledge."""

    def __init__(self, db_path: str, api_key: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

        genai.configure(api_key=api_key)
        self.db = lancedb.connect(db_path)

        # Create or get table
        try:
            self.table = self.db.open_table("knowledge")
        except Exception:
            # Create empty table with schema
            self.table = self.db.create_table(
                "knowledge",
                schema=KnowledgeEntry,
                mode="overwrite",
            )

    async def store(
        self,
        query: str,
        content: str,
        source_agent: str,
        topics: list[str] | None = None,
    ) -> str:
        """Store a new knowledge entry."""
        # Generate embedding
        embedding = await self._get_embedding(f"{query}\n{content[:500]}")

        entry_id = f"{source_agent}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        entry = KnowledgeEntry(
            id=entry_id,
            query=query,
            content=content,
            source_agent=source_agent,
            created_at=datetime.now().isoformat(),
            topics=",".join(topics) if topics else "",
            vector=embedding,
        )

        self.table.add([entry.model_dump()])
        return entry_id

    async def search(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search for similar knowledge entries."""
        # Generate query embedding
        query_embedding = await self._get_embedding(query)

        # Search with LanceDB
        results = self.table.search(query_embedding).limit(limit).to_list()

        # Filter by similarity and format results
        filtered = []
        for r in results:
            # LanceDB returns _distance, convert to similarity
            similarity = 1 - (r.get("_distance", 0) / 2)
            if similarity >= min_similarity:
                filtered.append(
                    {
                        "id": r.get("id"),
                        "query": r.get("query"),
                        "content": r.get("content"),
                        "source_agent": r.get("source_agent"),
                        "created_at": r.get("created_at"),
                        "similarity": similarity,
                    }
                )

        return filtered

    async def get_by_id(self, entry_id: str) -> dict[str, Any] | None:
        """Get a specific knowledge entry by ID."""
        results = self.table.search().where(f"id = '{entry_id}'").limit(1).to_list()
        if results:
            return results[0]
        return None

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Gemini."""
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]
