"""LangGraph-based orchestrator agent."""

import logging
import sys
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from .config import get_settings
from .router import AgentType, QueryRouter, RoutingDecision
from .synthesizer import AgentResponse, ResponseSynthesizer, SynthesizedResponse

sys.path.insert(0, "/app")
from shared.a2a_utils import A2AClient

# Set up module logger
logger = logging.getLogger("orchestrator-agent")


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
        logger.info("Initializing OrchestratorAgent...")
        self.settings = get_settings()
        self.router = QueryRouter(settings=self.settings)
        self.synthesizer = ResponseSynthesizer(settings=self.settings)
        self.graph = self._build_graph()
        logger.info("OrchestratorAgent initialization complete")

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
        logger.info(f"Routing query: {state['query'][:100]}...")
        try:
            routing = await self.router.route(state["query"])
            logger.info(f"Routed to agents: {[a.value for a in routing.agents]}")
            return {"routing": routing, "agent_responses": []}
        except Exception as e:
            logger.error(f"Routing failed: {str(e)}", exc_info=True)
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
        logger.debug("Checking knowledge base...")
        try:
            async with A2AClient(self.settings.knowledge_agent_url) as client:
                result = await client.send_task(
                    f"Search for relevant information about: {state['query']}"
                )
                content = self._extract_content(result)
                logger.debug(f"Knowledge base returned {len(content)} chars")
                return {
                    "knowledge_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="knowledge", content=content)],
                }
        except Exception as e:
            logger.warning(f"Knowledge check failed: {str(e)}")
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

        logger.info("Calling research agent...")
        try:
            async with A2AClient(self.settings.research_agent_url) as client:
                result = await client.send_task(state["query"])
                content = self._extract_content(result)
                logger.info(f"Research agent returned {len(content)} chars")
                return {
                    "research_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="research", content=content)],
                }
        except Exception as e:
            logger.error(f"Research agent call failed: {str(e)}", exc_info=True)
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
        logger.info("Calling explainer agent...")
        try:
            # Include research results in the context
            context = state.get("research_result", "")
            query = f"{state['query']}\n\nContext from research:\n{context}"

            async with A2AClient(self.settings.explainer_agent_url) as client:
                result = await client.send_task(query)
                content = self._extract_content(result)
                logger.info(f"Explainer agent returned {len(content)} chars")
                return {
                    "explainer_result": content,
                    "agent_responses": state["agent_responses"]
                    + [AgentResponse(agent_name="explainer", content=content)],
                }
        except Exception as e:
            logger.error(f"Explainer agent call failed: {str(e)}", exc_info=True)
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
        logger.info(f"Running orchestrator for query: {query[:100]}...")
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

        try:
            result = await self.graph.ainvoke(initial_state)

            if result.get("error"):
                logger.error(f"Orchestrator workflow error: {result['error']}")
                return SynthesizedResponse(
                    answer=f"Error: {result['error']}",
                    sources=[],
                    agents_used=[],
                )

            logger.info("Orchestrator workflow completed successfully")
            return result.get("final_response") or SynthesizedResponse(
                answer="No response generated.",
                sources=[],
                agents_used=[],
            )
        except Exception as e:
            logger.error(f"Orchestrator workflow failed: {str(e)}", exc_info=True)
            return SynthesizedResponse(
                answer=f"Error: {str(e)}",
                sources=[],
                agents_used=[],
            )
