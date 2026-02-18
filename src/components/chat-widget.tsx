import { useState, useRef, useEffect } from 'react'
import { Send, X, MessageCircle, Info } from 'lucide-react'

interface Message {
  id: string
  text: string
  sender: 'user' | 'agent'
  timestamp: Date
  sourcesUsed?: number
  ragUsed?: boolean
}

interface ChatResponse {
  response: string
  sources_used: number
  rag_used: boolean
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    text: "Hi there! 👋 How can I help you today?",
    sender: 'agent',
    timestamp: new Date(Date.now() - 60000),
    sourcesUsed: 0,
    ragUsed: false,
  },
]

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessageToBackend = async (message: string): Promise<ChatResponse> => {
    const response = await fetch('http://localhost:8000/api/v1/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: String(messages.length + 1),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    try {
      const data = await sendMessageToBackend(userMessage.text)
      
      const agentMessage: Message = {
        id: String(messages.length + 2),
        text: data.response,
        sender: 'agent',
        timestamp: new Date(),
        sourcesUsed: data.sources_used,
        ragUsed: data.rag_used,
      }

      setMessages(prev => [...prev, agentMessage])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      
      // Add error message to chat
      const errorMessage: Message = {
        id: String(messages.length + 2),
        text: "Sorry, I'm having trouble connecting. Please try again.",
        sender: 'agent',
        timestamp: new Date(),
        sourcesUsed: 0,
        ragUsed: false,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Chat Window */}
      <div
        className={`absolute bottom-20 right-0 w-96 max-w-[calc(100vw-24px)] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl flex flex-col transition-all duration-300 ease-out transform origin-bottom-right ${
          isOpen
            ? 'opacity-100 scale-100 pointer-events-auto'
            : 'opacity-0 scale-95 pointer-events-none'
        }`}
        style={{ height: isOpen ? '600px' : '0' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-t-2xl">
          <div>
            <h3 className="font-semibold text-lg">Chat Assistant</h3>
            <p className="text-sm text-blue-100">Always here to help</p>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            aria-label="Close chat"
          >
            <X size={20} />
          </button>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((message) => (
            <div key={message.id}>
              <div
                className={`flex ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-xs px-4 py-3 rounded-xl text-sm leading-relaxed ${
                    message.sender === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-none'
                  }`}
                >
                  {message.text}
                </div>
              </div>
              
              {/* Metadata for agent messages */}
              {message.sender === 'agent' && (message.sourcesUsed !== undefined || message.ragUsed !== undefined) && (
                <div className="flex justify-start mt-1">
                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    {message.ragUsed && (
                      <span className="flex items-center gap-1">
                        <Info size={12} />
                        RAG enabled
                      </span>
                    )}
                    {message.sourcesUsed !== undefined && message.sourcesUsed > 0 && (
                      <span>• {message.sourcesUsed} sources</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 dark:bg-slate-800 px-4 py-3 rounded-xl rounded-bl-none">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-800 rounded-b-2xl">
          {error && (
            <div className="mb-2 text-xs text-red-500 dark:text-red-400">
              {error}
            </div>
          )}
          <form onSubmit={handleSendMessage} className="flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white text-sm placeholder-slate-500 dark:placeholder-slate-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>

      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-14 h-14 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-200 flex items-center justify-center relative group ${
          isOpen ? 'pointer-events-none' : 'pointer-events-auto'
        }`}
      >
        <MessageCircle size={28} />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />

        {/* Tooltip */}
        <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
          Chat with us
        </div>
      </button>
    </div>
  )
}
