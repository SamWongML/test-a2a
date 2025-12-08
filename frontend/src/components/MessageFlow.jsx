import { MessageSquare, ArrowRight } from 'lucide-react'

const AGENT_COLORS = {
  orchestrator: 'var(--accent-orchestrator)',
  research: 'var(--accent-research)',
  explainer: 'var(--accent-explainer)',
  knowledge: 'var(--accent-knowledge)'
}

export default function MessageFlow({ messages }) {
  if (!messages?.length) return null

  return (
    <section className="message-flow-section fade-in">
      <h2>
        <MessageSquare size={18} />
        Agent Communication
      </h2>
      <div className="message-timeline">
        {messages.map((msg, index) => (
          <MessageItem key={`${msg.from}-${msg.to}-${index}`} message={msg} index={index} />
        ))}
      </div>
    </section>
  )
}

function MessageItem({ message, index }) {
  const { timestamp, from, to, content, type } = message

  const formatTime = (ts) => {
    if (!ts) return '--:--'
    const date = new Date(ts)
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="message-item slide-in" style={{ animationDelay: `${index * 50}ms` }}>
      <span className="message-time">{formatTime(timestamp)}</span>
      <div className="message-agents">
        <span className="message-from" style={{ color: AGENT_COLORS[from] || 'var(--text-primary)' }}>
          {from}
        </span>
        <ArrowRight size={14} className="message-arrow" />
        <span className="message-to" style={{ color: AGENT_COLORS[to] || 'var(--text-primary)' }}>
          {to}
        </span>
      </div>
      <span className="message-content">
        {content?.length > 100 ? `${content.substring(0, 100)}...` : content}
      </span>
    </div>
  )
}
