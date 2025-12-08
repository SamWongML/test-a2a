import { Sparkles, Clock, Users, Database } from 'lucide-react'

export default function ResponsePanel({ response, agents }) {
  if (!response) return null

  const { content, sources, duration } = response

  // Calculate agents used
  const agentsUsed = agents?.filter(a => a.status === 'complete').map(a => a.name) || []

  return (
    <section className="response-section fade-in">
      <div className="glass-card response-panel">
        <h2>
          <Sparkles size={20} />
          Synthesized Response
        </h2>
        <div className="response-content">
          {formatContent(content)}
        </div>
        <div className="response-meta">
          {duration && (
            <div className="response-meta-item">
              <Clock size={14} />
              <span>{duration}s total</span>
            </div>
          )}
          {agentsUsed.length > 0 && (
            <div className="response-meta-item">
              <Users size={14} />
              <span>{agentsUsed.join(', ')}</span>
            </div>
          )}
          {sources?.length > 0 && (
            <div className="response-meta-item">
              <Database size={14} />
              <span>{sources.length} sources</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function formatContent(content) {
  if (!content) return null

  // Basic markdown-like formatting
  const paragraphs = content.split('\n\n')
  
  return paragraphs.map((paragraph, i) => {
    // Check for code blocks
    if (paragraph.startsWith('```')) {
      const code = paragraph.replace(/```\w*\n?/g, '').replace(/```$/g, '')
      return <pre key={i}><code>{code}</code></pre>
    }
    
    // Inline code
    const parts = paragraph.split(/(`[^`]+`)/g)
    const formattedParts = parts.map((part, j) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={j}>{part.slice(1, -1)}</code>
      }
      return part
    })

    return <p key={i}>{formattedParts}</p>
  })
}
