"""CrewAI-based Research Agent for AI project discovery."""

import logging

from crewai import Agent, Crew, Process, Task

from shared.models import ModelFactory
from shared.token_manager import TokenManager

from .config import get_settings
from .tools import FirecrawlSearchTool, GitHubSearchTool
from .tools.firecrawl import FirecrawlScrapeTool
from .tools.github import GitHubRepoDetailsTool

# Set up module logger
logger = logging.getLogger("research-agent")


class ResearchAgent:
    """Research agent using CrewAI for AI project discovery."""

    def __init__(self):
        self.settings = get_settings()

        logger.info("Initializing ResearchAgent tools...")

        # Initialize tools
        self.firecrawl_search = FirecrawlSearchTool(api_key=self.settings.firecrawl_api_key)
        self.firecrawl_scrape = FirecrawlScrapeTool(api_key=self.settings.firecrawl_api_key)
        self.github_search = GitHubSearchTool(token=self.settings.github_token)
        self.github_details = GitHubRepoDetailsTool(token=self.settings.github_token)

        # Create provider-agnostic LLM for CrewAI
        logger.info("Creating CrewAI LLM...")
        self.llm = ModelFactory.create_crewai_llm(self.settings)

        # Create the crew
        logger.info("Creating research crew...")
        self.crew = self._create_crew()
        logger.info("ResearchAgent initialization complete")

    def _create_crew(self) -> Crew:
        """Create the research crew with specialized agents."""

        # Web Research Agent
        web_researcher = Agent(
            role="AI Web Researcher",
            goal="Find the latest information about AI projects and frameworks on the web",
            backstory="""You are an expert at finding and analyzing AI/ML content on the web.
            You use Firecrawl to search and scrape websites for the most relevant information
            about AI frameworks, tools, and projects.""",
            tools=[self.firecrawl_search, self.firecrawl_scrape],
            verbose=True,
            llm=self.llm,
        )

        # GitHub Research Agent
        github_researcher = Agent(
            role="GitHub AI Project Analyst",
            goal="Find and analyze popular AI/ML open source projects on GitHub",
            backstory="""You are an expert at discovering and evaluating open source AI projects
            on GitHub. You analyze repository metrics, documentation, and activity to identify
            the most promising and popular projects.""",
            tools=[self.github_search, self.github_details],
            verbose=True,
            llm=self.llm,
        )

        # Research Synthesizer Agent
        synthesizer = Agent(
            role="Research Synthesizer",
            goal="Combine web and GitHub research into comprehensive reports",
            backstory="""You are an expert at synthesizing research from multiple sources.
            You combine findings from web research and GitHub analysis to provide
            comprehensive, actionable insights about AI projects and trends.""",
            verbose=True,
            llm=self.llm,
        )

        return Crew(
            agents=[web_researcher, github_researcher, synthesizer],
            process=Process.sequential,
            verbose=True,
        )

    async def research(self, query: str) -> str:
        """Execute research on the given query."""
        logger.info(f"Starting research for query: {query[:100]}...")

        # Define tasks
        web_research_task = Task(
            description=f"""Search the web for information about: {query}
            
            Focus on:
            1. Recent news and announcements
            2. Technical documentation and tutorials
            3. Comparisons and reviews
            
            Use the firecrawl_search tool to find relevant content.""",
            expected_output="A summary of web research findings with sources",
            agent=self.crew.agents[0],  # web_researcher
        )

        github_research_task = Task(
            description=f"""Search GitHub for repositories related to: {query}
            
            Focus on:
            1. Most starred repositories
            2. Recently updated projects
            3. Active communities
            
            Use the github_search tool and get details for top projects.""",
            expected_output="A list of relevant GitHub repositories with descriptions and metrics",
            agent=self.crew.agents[1],  # github_researcher
        )

        synthesis_task = Task(
            description="""Combine the web research and GitHub findings into a comprehensive report.
            
            Include:
            1. Overview of the topic/technology
            2. Top repositories and their features
            3. Recent developments and trends
            4. Recommendations for getting started
            
            Format the output clearly with headers and bullet points.""",
            expected_output="A comprehensive research report",
            agent=self.crew.agents[2],  # synthesizer
            context=[web_research_task, github_research_task],
        )

        # Execute the crew
        try:
            # Refresh token before each call to ensure it's not expired
            logger.info("Refreshing Azure AD token before crew execution...")
            TokenManager.get_instance().set_environment_token()

            logger.info("Executing crew research workflow...")
            result = self.crew.kickoff(
                tasks=[web_research_task, github_research_task, synthesis_task]
            )
            logger.info("Research completed successfully")
            return str(result)
        except Exception as e:
            error_msg = f"Research failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    async def quick_search(self, query: str) -> str:
        """Execute a quick GitHub-only search."""
        logger.info(f"Starting quick search for query: {query[:100]}...")
        try:
            # Refresh token before each call to ensure it's not expired
            TokenManager.get_instance().set_environment_token()

            result = self.github_search._run(query)
            logger.info("Quick search completed successfully")
            return result
        except Exception as e:
            error_msg = f"Quick search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
