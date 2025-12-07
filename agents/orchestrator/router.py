"""Query router for determining which agents to call."""

import json
from enum import Enum

from pydantic import BaseModel

from shared.config import ModelProvider, Settings


class AgentType(str, Enum):
    """Available agent types."""

    RESEARCH = "research"
    EXPLAINER = "explainer"
    KNOWLEDGE = "knowledge"


class RoutingDecision(BaseModel):
    """Routing decision from the LLM."""

    agents: list[AgentType]
    reasoning: str
    check_knowledge_first: bool = True


ROUTING_PROMPT = """You are a query router for a multi-agent AI system. Analyze the user's query and determine which agents should handle it.

Available agents:
1. RESEARCH - Searches for new and popular AI/ML open source projects on GitHub. Use for:
   - Questions about latest AI frameworks, libraries, or tools
   - Finding trending repositories
   - Comparing open source projects
   
2. EXPLAINER - Provides detailed technical explanations with code snippets. Use for:
   - How to use a specific library or framework
   - Code examples and tutorials
   - Understanding technical concepts
   
3. KNOWLEDGE - Manages persistent memory and past research. Use for:
   - Retrieving previously researched information
   - Finding similar past queries
   - Getting contextual recommendations

Rules:
- You can select multiple agents if needed (e.g., research then explain)
- Always consider checking KNOWLEDGE first for efficiency
- For new topics, use RESEARCH then EXPLAINER
- For follow-up questions, KNOWLEDGE may be sufficient

User Query: {query}

Respond with a JSON object containing:
- "agents": list of agent names to call in order (e.g., ["RESEARCH", "EXPLAINER"])
- "reasoning": brief explanation of your choice
- "check_knowledge_first": true/false - whether to check knowledge base first

JSON Response:"""


class QueryRouter:
    """Routes queries to appropriate agents using LLM."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.model_provider
        self._init_model()

    def _init_model(self) -> None:
        """Initialize the LLM based on provider."""
        if self.provider == ModelProvider.GEMINI:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.google_api_key)
            self.model = genai.GenerativeModel(self.settings.gemini_model)
        elif self.provider == ModelProvider.AZURE_OPENAI:
            from shared.models import ModelFactory

            self.model = ModelFactory.create_genai_model(self.settings)

    async def route(self, query: str) -> RoutingDecision:
        """Determine which agents should handle the query."""
        prompt = ROUTING_PROMPT.format(query=query)

        if self.provider == ModelProvider.GEMINI:
            import google.generativeai as genai

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            result = json.loads(response.text)

        elif self.provider == ModelProvider.AZURE_OPENAI:
            response = self.model.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Convert agent strings to enums
        agents = [AgentType(a.lower()) for a in result.get("agents", ["research"])]

        return RoutingDecision(
            agents=agents,
            reasoning=result.get("reasoning", "Default routing"),
            check_knowledge_first=result.get("check_knowledge_first", True),
        )
