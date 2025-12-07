"""PydanticAI-based Explainer Agent for technology explanations."""

from pydantic_ai import Agent

from shared.models import ModelFactory

from .config import get_settings
from .models import TechnologyExplanation
from .tools import Context7Tool

EXPLAINER_SYSTEM_PROMPT = """You are an expert technology explainer specializing in AI/ML tools and frameworks.

Your task is to provide clear, detailed explanations of technologies with practical code examples.

When explaining a technology:
1. Start with a brief summary of what it is
2. Explain the core concepts and how it works
3. Provide practical use cases
4. Include working code snippets that demonstrate key features
5. List pros and cons
6. Mention related technologies

Always:
- Use accurate, up-to-date information
- Provide code examples that are complete and runnable
- Explain code snippets with comments
- Be practical and focus on real-world usage
"""


class ExplainerAgent:
    """Explainer agent using PydanticAI for structured explanations."""

    def __init__(self):
        self.settings = get_settings()
        self.context7 = Context7Tool(api_key=self.settings.context7_api_key)

        # Create PydanticAI agent with provider-agnostic model
        model = ModelFactory.create_pydantic_ai_model(self.settings)

        self.agent = Agent(
            model,
            output_type=TechnologyExplanation,
            system_prompt=EXPLAINER_SYSTEM_PROMPT,
        )

    async def explain(self, query: str, context: str = "") -> TechnologyExplanation:
        """Generate a detailed explanation for a technology."""

        # Try to get documentation from Context7
        doc_context = ""

        # Extract technology name from query
        tech_name = self._extract_tech_name(query)
        if tech_name:
            doc_context = await self.context7.get_documentation(tech_name)
            examples = await self.context7.search_examples(tech_name, "getting started")
            if examples:
                doc_context += f"\n\nCode Examples:\n{examples}"

        # Build the full prompt
        full_query = f"""Explain this technology/topic: {query}

{f"Additional Context: {context}" if context else ""}

{f"Documentation Reference: {doc_context}" if doc_context else ""}

Provide a detailed explanation with code examples."""

        # Run the PydanticAI agent
        result = await self.agent.run(full_query)
        return result.output

    async def quick_explain(self, query: str) -> str:
        """Generate a quick, text-only explanation."""
        result = await self.explain(query)

        # Format as readable text
        output = f"""# {result.name}

## Summary
{result.summary}

## Explanation
{result.detailed_explanation}

## Use Cases
{chr(10).join(f"- {uc}" for uc in result.use_cases)}
"""

        if result.code_snippets:
            output += "\n## Code Examples\n"
            for snippet in result.code_snippets:
                output += f"\n### {snippet.description}\n"
                output += f"```{snippet.language}\n{snippet.code}\n```\n"

        if result.pros:
            output += f"\n## Pros\n{chr(10).join(f'- {p}' for p in result.pros)}\n"

        if result.cons:
            output += f"\n## Cons\n{chr(10).join('- c' for c in result.cons)}\n"

        return output

    def _extract_tech_name(self, query: str) -> str | None:
        """Extract technology name from query."""
        # Common patterns for technology names
        query_lower = query.lower()

        # List of known technologies
        known_techs = [
            "langchain",
            "langgraph",
            "crewai",
            "autogen",
            "pydanticai",
            "agno",
            "phidata",
            "openai",
            "anthropic",
            "gemini",
            "azure",
            "pytorch",
            "tensorflow",
            "huggingface",
            "transformers",
            "fastapi",
            "flask",
            "django",
            "streamlit",
            "gradio",
            "pandas",
            "numpy",
            "scikit-learn",
            "xgboost",
            "lightgbm",
            "docker",
            "kubernetes",
            "redis",
            "postgresql",
            "mongodb",
        ]

        for tech in known_techs:
            if tech in query_lower:
                return tech

        # Try to get first noun-like word
        words = query.split()
        for word in words:
            if len(word) > 2 and word.isalpha():
                return word.lower()

        return None
