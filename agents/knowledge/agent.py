"""Agno-based Knowledge Manager Agent."""

import logging

from agno.agent import Agent

from shared.models import ModelFactory

from .config import get_settings
from .knowledge_base import KnowledgeBase
from .memory import SessionMemory

# Set up module logger
logger = logging.getLogger("knowledge-agent")

KNOWLEDGE_SYSTEM_PROMPT = """You are a Knowledge Manager for a multi-agent AI system.

Your responsibilities:
1. Store research findings and explanations from other agents
2. Retrieve relevant past information when queried
3. Identify similar past queries to avoid redundant research
4. Provide contextual recommendations based on conversation history

When asked to store information:
- Extract key topics and entities
- Summarize the content for efficient retrieval
- Confirm storage with a brief summary

When asked to search:
- Use semantic search to find relevant past information
- Rank results by relevance
- Provide a concise summary of what was found

Always be helpful and provide context about when information was stored and from which agent."""


class KnowledgeAgent:
    """Knowledge manager using Agno for memory and RAG."""

    def __init__(self):
        self.settings = get_settings()

        logger.info("Initializing KnowledgeAgent...")

        # Initialize knowledge base with Azure OpenAI embeddings
        logger.debug("Setting up knowledge base...")
        self.kb = KnowledgeBase(
            db_path=self.settings.vector_db_path,
            settings=self.settings,
        )

        # Initialize session memory
        self.memory = SessionMemory()

        # Create Agno agent with Azure OpenAI model
        logger.info("Creating Agno model...")
        model = ModelFactory.create_agno_model(self.settings)
        self.agent = Agent(
            model=model,
            description="Knowledge Manager for multi-agent system",
            instructions=KNOWLEDGE_SYSTEM_PROMPT,
            markdown=True,
        )
        logger.info("KnowledgeAgent initialization complete")

    async def process(self, query: str, session_id: str = "default") -> str:
        """Process a knowledge request."""
        logger.info(f"Processing knowledge request: {query[:100]}...")

        # Add to session memory
        self.memory.add_message(session_id, "user", query)

        # Determine the action
        query_lower = query.lower()

        if query_lower.startswith("store"):
            logger.debug("Handling store request")
            result = await self._handle_store(query)
        elif query_lower.startswith("search") or query_lower.startswith("find"):
            logger.debug("Handling search request")
            result = await self._handle_search(query)
        else:
            # Default: search for relevant information
            logger.debug("Handling default search request")
            result = await self._handle_search(query)

        # Add response to session memory
        self.memory.add_message(session_id, "assistant", result)

        logger.info("Knowledge request processed successfully")
        return result

    async def _handle_store(self, query: str) -> str:
        """Handle a store request."""
        # Parse the store request
        # Format: "Store this research finding:\nQuery: {query}\nAnswer: {answer}"
        try:
            lines = query.split("\n")
            original_query = ""
            content = ""
            source = "unknown"

            for i, line in enumerate(lines):
                if line.startswith("Query:"):
                    original_query = line[6:].strip()
                elif line.startswith("Answer:"):
                    content = "\n".join(lines[i:])
                    content = content[7:].strip()
                    break

            if not original_query:
                original_query = query[:100]
            if not content:
                content = query

            # Extract topics (simple approach)
            topics = self._extract_topics(f"{original_query} {content}")

            # Store in knowledge base
            entry_id = await self.kb.store(
                query=original_query,
                content=content,
                source_agent=source,
                topics=topics,
            )

            topics_str = ", ".join(topics) if topics else "general"
            return f"✅ Stored knowledge entry: {entry_id}\nTopics: {topics_str}"

        except Exception as e:
            logger.error(f"Failed to store knowledge: {str(e)}", exc_info=True)
            return f"❌ Failed to store: {str(e)}"

    async def _handle_search(self, query: str) -> str:
        """Handle a search request."""
        try:
            # Clean up query
            search_query = query
            for prefix in [
                "search for",
                "search",
                "find",
                "look for",
                "search for relevant information about:",
            ]:
                if search_query.lower().startswith(prefix):
                    search_query = search_query[len(prefix) :].strip()
                    break

            # Search knowledge base
            results = await self.kb.search(
                query=search_query,
                limit=self.settings.max_search_results,
            )

            if not results:
                return f"No relevant information found for: {search_query}"

            # Format results
            output_parts = [f"Found {len(results)} relevant entries:\n"]

            for i, r in enumerate(results, 1):
                similarity_pct = r.get("similarity", 0) * 100
                source_agent = r.get("source_agent", "unknown")
                query_text = r.get("query", "")[:100]
                content_text = r.get("content", "")[:500]
                output_parts.append(
                    f"**{i}. From {source_agent}** (Relevance: {similarity_pct:.0f}%)\n"
                    f"Query: {query_text}\n"
                    f"Content: {content_text}...\n"
                )

            return "\n---\n".join(output_parts)

        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            return f"Search error: {str(e)}"

    def _extract_topics(self, text: str) -> list[str]:
        """Extract topics from text."""
        # Simple keyword extraction
        keywords = [
            "langchain",
            "langgraph",
            "crewai",
            "autogen",
            "pydantic",
            "agno",
            "openai",
            "anthropic",
            "llm",
            "agent",
            "rag",
            "embedding",
            "vector",
            "memory",
            "tool",
            "mcp",
            "python",
            "javascript",
            "typescript",
            "api",
            "rest",
            "fastapi",
            "flask",
            "docker",
            "kubernetes",
            "azure",
            "google",
        ]

        text_lower = text.lower()
        found = [k for k in keywords if k in text_lower]

        return found[:5]  # Limit to 5 topics

    async def get_context(self, session_id: str) -> str:
        """Get conversation context for a session."""
        return self.memory.get_context_summary(session_id)
