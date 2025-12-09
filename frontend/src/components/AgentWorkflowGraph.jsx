import { useMemo } from 'react'

// Larger horizontal layout with proper proportions
const AGENTS = [
  { id: 'router', name: 'Router', icon: '⚡', x: 100, y: 100 },
  { id: 'knowledge', name: 'Knowledge', icon: '🧠', x: 350, y: 40 },
  { id: 'research', name: 'Research', icon: '🔬', x: 350, y: 100 },
  { id: 'explainer', name: 'Explainer', icon: '📚', x: 350, y: 160 },
  { id: 'synthesizer', name: 'Synthesizer', icon: '✨', x: 600, y: 100 }
]

const CONNECTIONS = [
  { from: 'router', to: 'knowledge' },
  { from: 'router', to: 'research' },
  { from: 'router', to: 'explainer' },
  { from: 'knowledge', to: 'synthesizer' },
  { from: 'research', to: 'synthesizer' },
  { from: 'explainer', to: 'synthesizer' }
]

const AGENT_COLORS = {
  router: '#a855f7',
  knowledge: '#f59e0b',
  research: '#3b82f6',
  explainer: '#10b981',
  synthesizer: '#a855f7'
}

function getAgentPos(agentId) {
  return AGENTS.find(a => a.id === agentId) || { x: 350, y: 100 }
}

export default function AgentWorkflowGraph({ agents = [], activeConnections = [] }) {
  const activeAgentIds = useMemo(() => {
    return agents.filter(a => a.status === 'active').map(a => a.id)
  }, [agents])

  const isConnectionActive = (from, to) => {
    return activeConnections.some(
      conn => (conn.from === from && conn.to === to) || 
              (conn.from === to && conn.to === from)
    )
  }

  // Create smooth curved path between two points
  const createCurvePath = (x1, y1, x2, y2) => {
    const dx = x2 - x1
    // Gentle horizontal curve - control points at 30% and 70%
    const cp1x = x1 + dx * 0.35
    const cp2x = x2 - dx * 0.35
    return `M ${x1} ${y1} C ${cp1x} ${y1}, ${cp2x} ${y2}, ${x2} ${y2}`
  }

  return (
    <div className="workflow-graph-container">
      <svg 
        viewBox="0 0 700 200" 
        className="workflow-graph-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Animated gradient for active connections */}
          <linearGradient id="activeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#a855f7" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#a855f7" stopOpacity="1" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0.2" />
          </linearGradient>

          {/* Glow filters */}
          {Object.entries(AGENT_COLORS).map(([id, color]) => (
            <filter key={id} id={`glow-${id}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur"/>
              <feFlood floodColor={color} result="color"/>
              <feComposite in="color" in2="blur" operator="in" result="glow"/>
              <feMerge>
                <feMergeNode in="glow"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          ))}
        </defs>

        {/* Curved connection lines */}
        <g className="workflow-connections">
          {CONNECTIONS.map(({ from, to }) => {
            const fromPos = getAgentPos(from)
            const toPos = getAgentPos(to)
            const active = isConnectionActive(from, to)
            
            const startX = fromPos.x + 55
            const endX = toPos.x - 55
            const pathD = createCurvePath(startX, fromPos.y, endX, toPos.y)
            
            return (
              <g key={`${from}-${to}`}>
                {/* Base curve */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                />
                {/* Active curve with electric pulse animation */}
                {active && (
                  <>
                    {/* Glowing base line */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={AGENT_COLORS[from]}
                      strokeWidth="2"
                      strokeOpacity="0.3"
                    />
                    {/* Electric pulse that shoots through */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={AGENT_COLORS[from]}
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeDasharray="20 200"
                      className="connection-active"
                    >
                      <animate
                        attributeName="stroke-dashoffset"
                        from="220"
                        to="0"
                        dur="1s"
                        repeatCount="indefinite"
                      />
                    </path>
                  </>
                )}
              </g>
            )
          })}
        </g>

        {/* Agent nodes */}
        <g className="workflow-nodes">
          {AGENTS.map(agent => {
            const isActive = activeAgentIds.includes(agent.id)
            const color = AGENT_COLORS[agent.id]
            
            return (
              <g 
                key={agent.id} 
                className={`workflow-node ${agent.id} ${isActive ? 'active' : ''}`}
                transform={`translate(${agent.x}, ${agent.y})`}
              >
                {/* Breathing glow ring */}
                {isActive && (
                  <rect
                    x="-57"
                    y="-18"
                    width="114"
                    height="36"
                    rx="18"
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    opacity="0.4"
                    className="node-glow-rect"
                  />
                )}
                
                {/* Main pill node */}
                <rect
                  x="-52"
                  y="-14"
                  width="104"
                  height="28"
                  rx="14"
                  fill={isActive ? `${color}20` : 'rgba(13, 13, 20, 0.95)'}
                  stroke={color}
                  strokeWidth={isActive ? 2 : 1}
                  filter={isActive ? `url(#glow-${agent.id})` : undefined}
                  className="node-pill"
                />
                
                {/* Icon and text */}
                <text
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={isActive ? '#fff' : 'rgba(255,255,255,0.85)'}
                  fontSize="12"
                  fontFamily="'Inter', system-ui, sans-serif"
                  fontWeight={isActive ? '600' : '500'}
                  letterSpacing="0.01em"
                >
                  <tspan>{agent.icon}</tspan>
                  <tspan dx="5">{agent.name}</tspan>
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
