import { useState, useCallback, useRef } from 'react'

const INITIAL_STATE = {
  agents: [],
  toolCalls: [],
  messages: [],
  response: null
}

export default function useEventStream() {
  const [state, setState] = useState(INITIAL_STATE)
  const abortControllerRef = useRef(null)

  const updateAgent = useCallback((agentId, updates) => {
    setState(prev => ({
      ...prev,
      agents: prev.agents.some(a => a.id === agentId)
        ? prev.agents.map(a => a.id === agentId ? { ...a, ...updates } : a)
        : [...prev.agents, { id: agentId, ...updates }]
    }))
  }, [])

  const addToolCall = useCallback((toolCall) => {
    setState(prev => ({
      ...prev,
      toolCalls: [...prev.toolCalls, toolCall]
    }))
  }, [])

  const updateToolCall = useCallback((name, updates) => {
    setState(prev => ({
      ...prev,
      toolCalls: prev.toolCalls.map(tc => 
        tc.name === name && tc.status === 'pending' 
          ? { ...tc, ...updates } 
          : tc
      )
    }))
  }, [])

  const addMessage = useCallback((message) => {
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, { ...message, timestamp: new Date().toISOString() }]
    }))
  }, [])

  const setResponse = useCallback((response) => {
    setState(prev => ({ ...prev, response }))
  }, [])

  const resetStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setState(INITIAL_STATE)
  }, [])

  const startStream = useCallback(async (query) => {
    abortControllerRef.current = new AbortController()
    const startTime = Date.now()

    try {
      const response = await fetch('/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              handleEvent(data, { updateAgent, addToolCall, updateToolCall, addMessage, setResponse })
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
          }
        }
      }

      // Calculate total duration
      const duration = ((Date.now() - startTime) / 1000).toFixed(1)
      setState(prev => ({
        ...prev,
        response: prev.response ? { ...prev.response, duration } : null
      }))

    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Stream error:', error)
        // Fallback to regular API call
        await fallbackToRegularApi(query, { updateAgent, setResponse })
      }
    }
  }, [updateAgent, addToolCall, updateToolCall, addMessage, setResponse])

  return {
    ...state,
    startStream,
    resetStream
  }
}

function handleEvent(event, handlers) {
  const { type, payload } = event
  const { updateAgent, addToolCall, updateToolCall, addMessage, setResponse } = handlers

  switch (type) {
    case 'agent_start':
      updateAgent(payload.agent, { status: 'active', output: '' })
      addMessage({
        from: 'orchestrator',
        to: payload.agent,
        content: payload.message || 'Starting task...'
      })
      break

    case 'agent_output':
      updateAgent(payload.agent, { 
        output: prev => (prev || '') + payload.content,
        status: 'active'
      })
      break

    case 'agent_complete':
      updateAgent(payload.agent, { 
        status: 'complete',
        duration: payload.duration,
        tokens: payload.tokens
      })
      addMessage({
        from: payload.agent,
        to: 'orchestrator',
        content: 'Task completed'
      })
      break

    case 'tool_call':
      addToolCall({
        name: payload.name,
        agent: payload.agent,
        input: payload.input,
        status: 'pending'
      })
      break

    case 'tool_result':
      updateToolCall(payload.name, {
        output: payload.output,
        status: 'complete'
      })
      break

    case 'message':
      addMessage({
        from: payload.from,
        to: payload.to,
        content: payload.content
      })
      break

    case 'synthesis':
    case 'complete':
      setResponse({
        content: payload.answer || payload.content,
        sources: payload.sources || []
      })
      break

    case 'error':
      updateAgent(payload.agent, { status: 'error' })
      break

    default:
      console.log('Unknown event type:', type)
  }
}

async function fallbackToRegularApi(query, { updateAgent, setResponse }) {
  // Fallback when SSE is not available - use regular A2A endpoint
  try {
    updateAgent('orchestrator', { status: 'active', output: 'Processing query...' })

    const response = await fetch('/api/a2a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tasks/send',
        params: {
          message: {
            role: 'user',
            parts: [{ text: query }]
          }
        },
        id: '1'
      })
    })

    const data = await response.json()
    
    if (data.result?.message?.parts?.[0]?.text) {
      updateAgent('orchestrator', { status: 'complete' })
      setResponse({
        content: data.result.message.parts[0].text,
        sources: data.result.metadata?.sources || []
      })
    }
  } catch (error) {
    console.error('Fallback API error:', error)
    updateAgent('orchestrator', { status: 'error', output: 'Failed to process query' })
  }
}
