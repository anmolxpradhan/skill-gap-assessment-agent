import { useEffect, useRef, useState } from 'react'

/** Strip structured data blocks (XML tags + all JSON code blocks) from display text. */
function stripDataBlocks(text) {
  // Remove XML-tagged data blocks
  text = text.replace(/<gap_analysis>[\s\S]*?<\/gap_analysis>/g, '')
  text = text.replace(/<learning_plan>[\s\S]*?<\/learning_plan>/g, '')
  // Remove ALL ```json code blocks — structured data never belongs in chat bubbles
  text = text.replace(/```json[\s\S]*?```/g, '')
  // Remove bare ``` blocks whose content looks like a JSON object (starts with {)
  text = text.replace(/```\s*(\{[\s\S]*?\})\s*```/g, '')
  // Collapse excess blank lines left behind
  return text.replace(/\n{3,}/g, '\n\n').trim()
}

/** Lightweight inline markdown renderer — handles **bold**, *italic*, and line breaks. */
function renderMarkdown(text) {
  const parts = []
  let remaining = text
  let key = 0

  while (remaining.length) {
    const boldIdx = remaining.indexOf('**')
    const italicIdx = remaining.indexOf('*')
    const first =
      boldIdx === -1 ? italicIdx : italicIdx === -1 ? boldIdx : Math.min(boldIdx, italicIdx)

    if (first === -1) {
      parts.push(<span key={key++}>{remaining}</span>)
      break
    }

    if (first > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, first)}</span>)
      remaining = remaining.slice(first)
    }

    if (remaining.startsWith('**')) {
      const end = remaining.indexOf('**', 2)
      if (end === -1) { parts.push(<span key={key++}>{remaining}</span>); break }
      parts.push(<strong key={key++}>{remaining.slice(2, end)}</strong>)
      remaining = remaining.slice(end + 2)
    } else {
      const end = remaining.indexOf('*', 1)
      if (end === -1) { parts.push(<span key={key++}>{remaining}</span>); break }
      parts.push(<em key={key++}>{remaining.slice(1, end)}</em>)
      remaining = remaining.slice(end + 1)
    }
  }

  return parts
}

function MessageBubble({ role, content }) {
  const isAssistant = role === 'assistant'
  const cleaned = isAssistant ? stripDataBlocks(content) : content
  if (!cleaned) return null
  const lines = cleaned.split('\n')

  return (
    <div className={`message ${isAssistant ? 'message-assistant' : 'message-user'}`}>
      {isAssistant && <div className="avatar">✦</div>}
      <div className="bubble">
        {lines.map((line, i) =>
          line.trim() === '' ? (
            <br key={i} />
          ) : (
            <p key={i}>{renderMarkdown(line)}</p>
          ),
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="message message-assistant">
      <div className="avatar">✦</div>
      <div className="bubble typing-bubble">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  )
}

export default function ChatInterface({ messages, onSend, loading, phase, onViewPlan, gapAnalysis, learningPlan }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading) inputRef.current?.focus()
  }, [loading])

  const handleSend = () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    onSend(text)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isComplete = phase === 3
  const needsPlan = gapAnalysis && !learningPlan && !loading

  return (
    <div className="chat-interface">
      <div className="messages-list">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        {isComplete ? (
          <div className="assessment-done-bar">
            <span>Assessment complete</span>
            <button className="view-plan-btn" onClick={onViewPlan}>
              View Learning Plan →
            </button>
          </div>
        ) : (
          <>
            {needsPlan && (
              <button
                className="get-plan-btn"
                onClick={() => onSend('Please generate the learning plan now.')}
                disabled={loading}
              >
                Generate Learning Plan →
              </button>
            )}
            <div className="chat-input-row">
              <textarea
                ref={inputRef}
                className="chat-textarea"
                placeholder="Type your answer… (Enter to send, Shift+Enter for newline)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                disabled={loading}
                rows={2}
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!input.trim() || loading}
              >
                Send
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
