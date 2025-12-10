import { useMemo } from 'react'

// Larger layout with proper proportions
const AGENTS = [
  { id: 'router', name: 'Router', icon: '⚡', x: 150, y: 200 },
  { id: 'knowledge', name: 'Knowledge', icon: '🧠', x: 450, y: 80 },
  { id: 'research', name: 'Research', icon: '🔬', x: 450, y: 200 },
  { id: 'explainer', name: 'Explainer', icon: '📚', x: 450, y: 320 },
  { id: 'synthesizer', name: 'Synthesizer', icon: '✨', x: 750, y: 200 }
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
  return AGENTS.find(a => a.id === agentId) || { x: 450, y: 200 }
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
    const cp1x = x1 + dx * 0.4
    const cp2x = x2 - dx * 0.4
    return `M ${x1} ${y1} C ${cp1x} ${y1}, ${cp2x} ${y2}, ${x2} ${y2}`
  }

  return (
    <div className="workflow-graph-container">
      <svg 
        viewBox="0 0 900 400" 
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
              <feGaussianBlur stdDeviation="4" result="blur"/>
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
            
            const startX = fromPos.x + 80 // Half width of larger node
            const endX = toPos.x - 80
            const pathD = createCurvePath(startX, fromPos.y, endX, toPos.y)
            
            return (
              <g key={`${from}-${to}`}>
                {/* Base curve */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth="3"
                  strokeDasharray="8 6"
                />
                {/* Active curve with electric pulse animation */}
                {active && (
                  <>
                    {/* Glowing base line */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={AGENT_COLORS[from]}
                      strokeWidth="3"
                      strokeOpacity="0.3"
                    />
                    {/* Electric pulse that shoots through */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={AGENT_COLORS[from]}
                      strokeWidth="4"
                      strokeLinecap="round"
                      strokeDasharray="30 300"
                      className="connection-active"
                    >
                      <animate
                        attributeName="stroke-dashoffset"
                        from="330"
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
                    x="-85"
                    y="-28"
                    width="170"
                    height="56"
                    rx="28"
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    opacity="0.4"
                    className="node-glow-rect"
                  />
                )}
                
                {/* Main pill node - Larger dimensions */}
                <rect
                  x="-80"
                  y="-24"
                  width="160"
                  height="48"
                  rx="24"
                  fill={isActive ? `${color}25` : 'rgba(13, 13, 20, 0.95)'}
                  stroke={color}
                  strokeWidth={isActive ? 2.5 : 1.5}
                  filter={isActive ? `url(#glow-${agent.id})` : undefined}
                  className="node-pill"
                />
                
                {/* Icon and text - Larger text */}
                <text
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={isActive ? '#fff' : 'rgba(255,255,255,0.9)'}
                  fontSize="15"
                  fontFamily="'Inter', system-ui, sans-serif"
                  fontWeight={isActive ? '600' : '500'}
                  letterSpacing="0.02em"
                >
                  <tspan fontSize="18" dy="1">{agent.icon}</tspan>
                  <tspan dx="8">{agent.name}</tspan>
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
