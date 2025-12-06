"""Pydantic models for structured explainer outputs."""

from pydantic import BaseModel, Field


class CodeSnippet(BaseModel):
    """A code snippet with language and description."""

    language: str = Field(description="Programming language (e.g., python, javascript)")
    code: str = Field(description="The code snippet")
    description: str = Field(description="What this code does")
    filename: str | None = Field(default=None, description="Suggested filename")


class TechnologyExplanation(BaseModel):
    """Structured explanation of a technology."""

    name: str = Field(description="Name of the technology")
    summary: str = Field(description="Brief 1-2 sentence summary")
    detailed_explanation: str = Field(description="Detailed explanation of the technology")
    use_cases: list[str] = Field(description="Common use cases")
    code_snippets: list[CodeSnippet] = Field(
        default_factory=list,
        description="Code examples demonstrating the technology",
    )
    pros: list[str] = Field(default_factory=list, description="Advantages")
    cons: list[str] = Field(default_factory=list, description="Disadvantages or limitations")
    related_technologies: list[str] = Field(
        default_factory=list,
        description="Related or alternative technologies",
    )
    documentation_links: list[str] = Field(
        default_factory=list,
        description="Links to official documentation",
    )


class QuickExplanation(BaseModel):
    """Quick explanation without code snippets."""

    name: str = Field(description="Name of the technology")
    summary: str = Field(description="Brief explanation")
    key_features: list[str] = Field(description="Main features")


class ExplainerResponse(BaseModel):
    """Response from the explainer agent."""

    explanation: TechnologyExplanation | QuickExplanation
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the explanation")
