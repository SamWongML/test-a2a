"""Agno-based Knowledge Manager Agent."""

from agno.agent import Agent
from agno.models.google import Gemini

from .config import get_settings
from .knowledge_base import KnowledgeBase
from .memory import SessionMemory

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

        # Initialize knowledge base
        self.kb = KnowledgeBase(
            db_path=self.settings.vector_db_path,
            api_key=self.settings.google_api_key,
        )

        # Initialize session memory
        self.memory = SessionMemory()

        # Create Agno agent
        self.agent = Agent(
            model=Gemini(id=self.settings.gemini_model, api_key=self.settings.google_api_key),
            description="Knowledge Manager for multi-agent system",
            instructions=KNOWLEDGE_SYSTEM_PROMPT,
            markdown=True,
        )

    async def process(self, query: str, session_id: str = "default") -> str:
        """Process a knowledge request."""

        # Add to session memory
        self.memory.add_message(session_id, "user", query)

        # Determine the action
        query_lower = query.lower()

        if query_lower.startswith("store"):
            result = await self._handle_store(query)
        elif query_lower.startswith("search") or query_lower.startswith("find"):
            result = await self._handle_search(query)
        else:
            # Default: search for relevant information
            result = await self._handle_search(query)

        # Add response to session memory
        self.memory.add_message(session_id, "assistant", result)

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

            return f"✅ Stored knowledge entry: {entry_id}\nTopics: {', '.join(topics) if topics else 'general'}"

        except Exception as e:
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
                output_parts.append(
                    f"**{i}. From {r.get('source_agent', 'unknown')}** (Relevance: {similarity_pct:.0f}%)\n"
                    f"Query: {r.get('query', '')[:100]}\n"
                    f"Content: {r.get('content', '')[:500]}...\n"
                )

            return "\n---\n".join(output_parts)

        except Exception as e:
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
            "gemini",
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
        ]

        text_lower = text.lower()
        found = [k for k in keywords if k in text_lower]

        return found[:5]  # Limit to 5 topics

    async def get_context(self, session_id: str) -> str:
        """Get conversation context for a session."""
        return self.memory.get_context_summary(session_id)
