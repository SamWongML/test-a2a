import { Send, Loader2 } from 'lucide-react'

export default function QueryInput({ value, onChange, onSubmit, isLoading }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <form className="query-input-wrapper" onSubmit={onSubmit}>
      <input
        type="text"
        className="query-input"
        placeholder="Ask anything about AI agents, frameworks, or technologies..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
      />
      <button 
        type="submit" 
        className={`submit-button ${isLoading ? 'loading' : ''}`}
        disabled={isLoading || !value.trim()}
      >
        {isLoading ? (
          <Loader2 size={20} className="animate-spin" />
        ) : (
          <>
            <Send size={18} />
            Send
          </>
        )}
      </button>
    </form>
  )
}
