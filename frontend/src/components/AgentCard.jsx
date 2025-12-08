import { Bot, Clock, Hash } from 'lucide-react'

const AGENT_ICONS = {
  orchestrator: '🎛️',
  research: '🔬',
  explainer: '📚',
  knowledge: '🧠'
}

export default function AgentCard({ agent }) {
  const { id, name, framework, port, status, output, tokens, duration } = agent

  return (
    <div className={`glass-card agent-card ${id}`}>
      <div className="agent-card-header">
        <div className="agent-card-title">
          <span style={{ fontSize: '1.25rem' }}>{AGENT_ICONS[id] || <Bot size={20} />}</span>
          <div>
            <h3>{name} Agent</h3>
            <span className="framework">{framework} • Port {port}</span>
          </div>
        </div>
        <div className="agent-status">
          <span className={`status-dot ${status}`}></span>
          <span className={`status-dot ${status === 'active' ? 'active' : ''}`}></span>
          <span className={`status-dot ${status === 'complete' ? 'active' : ''}`}></span>
        </div>
      </div>
      
      <div className="agent-card-content">
        {output ? (
          <div className="agent-output">
            {output}
            {status === 'active' && <span className="streaming-cursor"></span>}
          </div>
        ) : (
          <div className="empty-state">
            <Bot size={32} />
            <p>Waiting for query...</p>
          </div>
        )}
      </div>

      <div className="agent-card-footer">
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={12} />
          {duration ? `${duration}s` : '--'}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Hash size={12} />
          {tokens ? `${tokens.toLocaleString()} tokens` : '--'}
        </span>
      </div>
    </div>
  )
}
