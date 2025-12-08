import { Wrench, ChevronRight } from 'lucide-react'

export default function ToolCallsSection({ toolCalls }) {
  if (!toolCalls?.length) return null

  return (
    <section className="tool-calls-section fade-in">
      <h2>
        <Wrench size={18} />
        Tool Calls
      </h2>
      <div className="tool-calls-grid">
        {toolCalls.map((call, index) => (
          <ToolCallCard key={`${call.name}-${index}`} call={call} />
        ))}
      </div>
    </section>
  )
}

function ToolCallCard({ call }) {
  const { name, agent, input, output, status } = call

  return (
    <div className="glass-card tool-call-card slide-in">
      <div className="tool-call-header">
        <Wrench size={14} />
        <span className="tool-call-name">{name}</span>
        <span className="tool-call-agent">{agent}</span>
      </div>
      <div className="tool-call-body">
        {input && (
          <>
            <div className="tool-call-label">Input</div>
            <pre className="tool-call-data">
              {typeof input === 'string' ? input : JSON.stringify(input, null, 2)}
            </pre>
          </>
        )}
        {output && (
          <>
            <div className="tool-call-label">Output</div>
            <pre className="tool-call-data">
              {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
            </pre>
          </>
        )}
        {status === 'pending' && (
          <div className="tool-call-label" style={{ color: 'var(--status-pending)' }}>
            Executing...
          </div>
        )}
      </div>
    </div>
  )
}
