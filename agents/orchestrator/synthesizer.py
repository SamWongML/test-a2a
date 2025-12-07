"""Response synthesizer for combining agent outputs."""

from pydantic import BaseModel

from shared.config import ModelProvider, Settings


class AgentResponse(BaseModel):
    """Response from an individual agent."""

    agent_name: str
    content: str
    success: bool = True
    error: str | None = None


class SynthesizedResponse(BaseModel):
    """Final synthesized response."""

    answer: str
    sources: list[str]
    agents_used: list[str]


SYNTHESIS_PROMPT = """You are a response synthesizer. Combine the following agent responses into a coherent, comprehensive answer for the user.

User Query: {query}

Agent Responses:
{agent_responses}

Instructions:
1. Synthesize the information into a clear, well-structured response
2. Highlight key findings from each agent
3. If there are code snippets, preserve them with proper formatting
4. If agents provided conflicting information, note this
5. Keep the response focused and actionable

Provide a comprehensive answer:"""


class ResponseSynthesizer:
    """Synthesizes responses from multiple agents."""

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

    async def synthesize(
        self,
        query: str,
        responses: list[AgentResponse],
    ) -> SynthesizedResponse:
        """Combine agent responses into a final answer."""

        # If only one successful response, return it directly
        successful = [r for r in responses if r.success]
        if len(successful) == 1:
            return SynthesizedResponse(
                answer=successful[0].content,
                sources=[successful[0].agent_name],
                agents_used=[r.agent_name for r in responses],
            )

        # Format agent responses for the prompt
        formatted_responses = "\n\n".join(
            [
                f"=== {r.agent_name} ===\n{r.content if r.success else f'Error: {r.error}'}"
                for r in responses
            ]
        )

        prompt = SYNTHESIS_PROMPT.format(
            query=query,
            agent_responses=formatted_responses,
        )

        if self.provider == ModelProvider.GEMINI:
            import google.generativeai as genai

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.3),
            )
            answer = response.text

        elif self.provider == ModelProvider.AZURE_OPENAI:
            response = self.model.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            answer = response.choices[0].message.content

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return SynthesizedResponse(
            answer=answer,
            sources=[r.agent_name for r in successful],
            agents_used=[r.agent_name for r in responses],
        )
