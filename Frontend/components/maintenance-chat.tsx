'use client'

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'
import { ArrowUp, Bot, CheckCircle2 } from 'lucide-react'

type Message = {
  id: number
  role: 'assistant' | 'user'
  content: string
}

const suggestions = [
  'I forgot my password',
  'My computer is slow',
  "I can't connect to Wi-Fi",
  'I received a suspicious email',
]

const responses = [
  "I can help you with that. Let's start with the basics, then we can work through the issue step by step.",
  'Thanks for letting me know. I recommend restarting the affected application or device first. If the problem continues, I can guide you through a few more checks.',
  'I can help troubleshoot this. Could you tell me which device you are using and when you first noticed the problem?',
]

function getResponse(message: string) {
  const text = message.toLowerCase()
  if (text.includes('wi-fi') || text.includes('wifi')) {
    return 'I can help you with that. First, check whether Wi-Fi is enabled on your device. Then try disconnecting and reconnecting to the network.\n\nIf the problem persists, I can help you troubleshoot it step by step.'
  }
  if (text.includes('password')) {
    return 'I can help you reset it. Select “Forgot password” on the sign-in screen and follow the instructions sent to your work email. Avoid sharing your password with anyone.'
  }
  if (text.includes('slow')) {
    return 'Let’s speed things up. Close any apps you are not using, restart your computer, and check that you have enough free storage. I can help investigate further if it is still slow.'
  }
  if (text.includes('suspicious') || text.includes('email')) {
    return 'Do not click links, download attachments, or reply to the message. Report it using your organisation’s phishing button, then delete it. I can help you review the warning signs if needed.'
  }
  return responses[message.length % responses.length]
}

export function MaintenanceChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: "Bonjour ! Je suis mAIntenance & Assistance. Décrivez votre problème informatique et je vous aiderai à trouver une solution.",
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const nextId = useRef(2)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const sendMessage = (value = input) => {
    const content = value.trim()
    if (!content || isTyping) return
    setMessages((current) => [...current, { id: nextId.current++, role: 'user', content }])
    setInput('')
    setIsTyping(true)
    window.setTimeout(() => {
      setMessages((current) => [...current, { id: nextId.current++, role: 'assistant', content: getResponse(content) }])
      setIsTyping(false)
    }, 800)
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    sendMessage()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
      event.preventDefault()
      sendMessage()
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-0 text-foreground sm:p-6">
      <section className="flex h-dvh w-full max-w-[920px] flex-col overflow-hidden border-border bg-card sm:h-[calc(100dvh-3rem)] sm:rounded-2xl sm:border sm:shadow-sm" aria-label="mAIntenance & Assistance chat">
        <header className="flex items-center justify-between border-b border-border px-5 py-4 sm:px-7">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Bot className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight sm:text-base">mAIntenance &amp; Assistance</h1>
              <p className="text-xs text-muted-foreground">Votre assistant intelligent pour le support informatique.</p>
            </div>
          </div>
          {/*<div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
            <CheckCircle2 className="size-3.5" aria-hidden="true" />
            <span>Online</span>
          </div>*/}
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-12 sm:py-8">
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            {messages.map((message) => (
              <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && (
                  <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary" aria-hidden="true">
                    <Bot className="size-3.5" />
                  </div>
                )}
                <div className={`max-w-[82%] whitespace-pre-line rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'rounded-br-md bg-primary text-primary-foreground' : 'rounded-bl-md bg-muted text-foreground'}`}>
                  {message.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex items-center gap-3" aria-label="Assistant is typing">
                <div className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-primary"><Bot className="size-3.5" /></div>
                <div className="rounded-2xl rounded-bl-md bg-muted px-4 py-3"><span className="flex gap-1"><i className="size-1.5 animate-pulse rounded-full bg-muted-foreground" /><i className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:150ms]" /><i className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:300ms]" /></span></div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {messages.length === 1 && (
            <div className="mx-auto mt-8 max-w-2xl">
              <p className="mb-3 text-xs font-medium text-muted-foreground">
                Exemples de questions
              </p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => { setInput(suggestion); inputRef.current?.focus() }} className="rounded-full border border-border bg-background px-3.5 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary">
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-border bg-card px-4 py-4 sm:px-12 sm:py-5">
          <form onSubmit={handleSubmit} className="mx-auto flex max-w-2xl items-end gap-2 rounded-2xl border border-input bg-background p-2 shadow-xs focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
            <label htmlFor="chat-input" className="sr-only">Décrivez votre problème informatique</label>
            <textarea ref={inputRef} id="chat-input" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleKeyDown} placeholder="Décrivez votre problème..." rows={1} className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground/70" />
            <button type="submit" disabled={!input.trim() || isTyping} aria-label="Send message" className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-35">
              <ArrowUp className="size-4" aria-hidden="true" />
            </button>
          </form>
          {/*<p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-muted-foreground">For urgent security incidents, contact your IT service desk directly.</p>*/}
        </div>
      </section>
    </main>
  )
}
