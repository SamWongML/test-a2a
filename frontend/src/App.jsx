import { useState, useCallback, useRef, useEffect } from 'react'
import { Sparkles } from 'lucide-react'
import QueryInput from './components/QueryInput'
import AgentWorkflowGraph from './components/AgentWorkflowGraph'
import AgentGrid from './components/AgentGrid'
import ToolCallsSection from './components/ToolCallsSection'
import MessageFlow from './components/MessageFlow'
import ResponsePanel from './components/ResponsePanel'
import useEventStream from './hooks/useEventStream'

export default function App() {
  const [query, setQuery] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const { 
    agents, 
    toolCalls, 
    messages, 
    response, 
    activeConnections,
    startStream, 
    resetStream 
  } = useEventStream()

  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault()
    if (!query.trim() || isStreaming) return
    
    setIsStreaming(true)
    resetStream()
    
    try {
      await startStream(query)
    } finally {
      setIsStreaming(false)
    }
  }, [query, isStreaming, startStream, resetStream])

  return (
    <div className="app-container">
      <header className="header">
        <h1>
          <Sparkles size={32} style={{ display: 'inline', marginRight: '0.5rem' }} />
          A2A Multi-Agent System
        </h1>
        <p>Real-time AI orchestration with streaming agent communication</p>
      </header>

      <section className="query-section">
        <QueryInput
          value={query}
          onChange={setQuery}
          onSubmit={handleSubmit}
          isLoading={isStreaming}
        />
      </section>

      <AgentWorkflowGraph agents={agents} activeConnections={activeConnections} />

      <section className="agents-section">
        <AgentGrid agents={agents} />
      </section>

      {toolCalls.length > 0 && (
        <ToolCallsSection toolCalls={toolCalls} />
      )}

      {messages.length > 0 && (
        <MessageFlow messages={messages} />
      )}

      {response && (
        <ResponsePanel response={response} agents={agents} />
      )}
    </div>
  )
}
