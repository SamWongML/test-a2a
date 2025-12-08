import AgentCard from './AgentCard'

const DEFAULT_AGENTS = [
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    framework: 'LangGraph',
    port: 8000,
    status: 'idle',
    output: ''
  },
  {
    id: 'research',
    name: 'Research',
    framework: 'CrewAI',
    port: 8001,
    status: 'idle',
    output: ''
  },
  {
    id: 'explainer',
    name: 'Explainer',
    framework: 'PydanticAI',
    port: 8002,
    status: 'idle',
    output: ''
  },
  {
    id: 'knowledge',
    name: 'Knowledge',
    framework: 'Agno',
    port: 8003,
    status: 'idle',
    output: ''
  }
]

export default function AgentGrid({ agents }) {
  // Merge incoming agents with defaults
  const mergedAgents = DEFAULT_AGENTS.map(defaultAgent => {
    const incoming = agents?.find(a => a.id === defaultAgent.id)
    return incoming ? { ...defaultAgent, ...incoming } : defaultAgent
  })

  return (
    <div className="agents-grid">
      {mergedAgents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}
