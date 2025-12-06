"""LangGraph-based orchestrator agent."""

import asyncio
import sys
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from .config import get_settings
from .router import AgentType, QueryRouter, RoutingDecision
from .synthesizer import AgentResponse, ResponseSynthesizer, SynthesizedResponse

sys.path.insert(0, "/app")
from shared.a2a_utils import A2AClient


class OrchestratorState(TypedDict):
    """State for the orchestrator workflow."""

    query: str
    routing: RoutingDecision | None
    knowledge_result: str | None
    research_result: str | None
    explainer_result: str | None
    agent_responses: list[AgentResponse]
    final_response: SynthesizedResponse | None
    error: str | None


class OrchestratorAgent:
    """Main orchestrator using LangGraph for workflow management."""

    def __init__(self):
        self.settings = get_settings()
        self.router = QueryRouter(
            api_key=self.settings.google_api_key,
            model=self.settings.gemini_model,
        )
        self.synthesizer = ResponseSynthesizer(
            api_key=self.settings.google_api_key,
            model=self.settings.gemini_model,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("check_knowledge", self._check_knowledge)
        workflow.add_node("call_research", self._call_research)
        workflow.add_node("call_explainer", self._call_explainer)
        workflow.add_node("synthesize", self._synthesize_response)

        # Set entry point
        workflow.set_entry_point("route_query")

        # Add edges
        workflow.add_conditional_edges(
            "route_query",
            self._decide_next_step,
            {
                "check_knowledge": "check_knowledge",
                "call_agents": "call_research",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "check_knowledge",
            self._knowledge_sufficient,
            {
                "sufficient": "synthesize",
                "need_more": "call_research",
            },
        )

        workflow.add_conditional_edges(
            "call_research",
            self._need_explainer,
            {
                "yes": "call_explainer",
                "no": "synthesize",
            },
        )

        workflow.add_edge("call_explainer", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def _route_query(self, state: OrchestratorState) -> dict:
        """Route the query to determine which agents to call."""
        try:
            routing = await self.router.route(state["query"])
            return {"routing": routing, "agent_responses": []}
        except Exception as e:
            return {"error": f"Routing failed: {str(e)}"}

    def _decide_next_step(
        self, state: OrchestratorState
    ) -> Literal["check_knowledge", "call_agents", "error"]:
        """Decide the next step based on routing."""
        if state.get("error"):
            return "error"
        routing = state.get("routing")
        if routing and routing.check_knowledge_first:
            return "check_knowledge"
        return "call_agents"

    async def _check_knowledge(self, state: OrchestratorState) -> dict:
        """Check the knowledge base for existing information."""
        try:
            async with A2AClient(self.settings.knowledge_agent_url) as client:
                result = await client.send_task(
                    f"Search for relevant information about: {state['query']}"
                )
                content = self._extract_content(result)
                return {
                    "knowledge_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="knowledge", content=content)],
                }
        except Exception as e:
            # Knowledge check failed, continue with other agents
            return {"knowledge_result": None}

    def _knowledge_sufficient(self, state: OrchestratorState) -> Literal["sufficient", "need_more"]:
        """Check if knowledge base result is sufficient."""
        result = state.get("knowledge_result")
        if result and len(result) > 100 and "no relevant" not in result.lower():
            return "sufficient"
        return "need_more"

    async def _call_research(self, state: OrchestratorState) -> dict:
        """Call the research agent."""
        routing = state.get("routing")
        if routing and AgentType.RESEARCH not in routing.agents:
            return {"research_result": None}

        try:
            async with A2AClient(self.settings.research_agent_url) as client:
                result = await client.send_task(state["query"])
                content = self._extract_content(result)
                return {
                    "research_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="research", content=content)],
                }
        except Exception as e:
            return {
                "research_result": None,
                "agent_responses": state["agent_responses"]
                + [
                    AgentResponse(
                        agent_name="research",
                        content="",
                        success=False,
                        error=str(e),
                    )
                ],
            }

    def _need_explainer(self, state: OrchestratorState) -> Literal["yes", "no"]:
        """Check if explainer agent is needed."""
        routing = state.get("routing")
        if routing and AgentType.EXPLAINER in routing.agents:
            return "yes"
        return "no"

    async def _call_explainer(self, state: OrchestratorState) -> dict:
        """Call the explainer agent."""
        try:
            # Include research results in the context
            context = state.get("research_result", "")
            query = f"{state['query']}\n\nContext from research:\n{context}"

            async with A2AClient(self.settings.explainer_agent_url) as client:
                result = await client.send_task(query)
                content = self._extract_content(result)
                return {
                    "explainer_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="explainer", content=content)],
                }
        except Exception as e:
            return {
                "explainer_result": None,
                "agent_responses": state["agent_responses"]
                + [
                    AgentResponse(
                        agent_name="explainer",
                        content="",
                        success=False,
                        error=str(e),
                    )
                ],
            }

    async def _synthesize_response(self, state: OrchestratorState) -> dict:
        """Synthesize final response from all agent outputs."""
        responses = state.get("agent_responses", [])
        if not responses:
            return {
                "final_response": SynthesizedResponse(
                    answer="I couldn't find relevant information for your query.",
                    sources=[],
                    agents_used=[],
                )
            }

        final = await self.synthesizer.synthesize(state["query"], responses)

        # Store the result in knowledge base for future queries
        try:
            async with A2AClient(self.settings.knowledge_agent_url) as client:
                await client.send_task(
                    f"Store this research finding:\nQuery: {state['query']}\nAnswer: {final.answer}"
                )
        except Exception:
            pass  # Don't fail if storage fails

        return {"final_response": final}

    def _extract_content(self, result: dict) -> str:
        """Extract content from A2A response."""
        try:
            parts = result.get("result", {}).get("message", {}).get("parts", [])
            return parts[0].get("text", "") if parts else ""
        except Exception:
            return str(result)

    async def run(self, query: str) -> SynthesizedResponse:
        """Run the orchestrator workflow."""
        initial_state: OrchestratorState = {
            "query": query,
            "routing": None,
            "knowledge_result": None,
            "research_result": None,
            "explainer_result": None,
            "agent_responses": [],
            "final_response": None,
            "error": None,
        }

        result = await self.graph.ainvoke(initial_state)

        if result.get("error"):
            return SynthesizedResponse(
                answer=f"Error: {result['error']}",
                sources=[],
                agents_used=[],
            )

        return result.get("final_response") or SynthesizedResponse(
            answer="No response generated.",
            sources=[],
            agents_used=[],
        )
