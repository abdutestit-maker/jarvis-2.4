export interface PresenceMessage { id: string; role: 'jarvis' | 'user'; text: string; timestamp: number; }

export function boundedMessages(messages: PresenceMessage[]): PresenceMessage[] {
  return messages.slice(-20);
}

export function MessageStream({ messages }: { messages: PresenceMessage[] }) {
  return <section className="messageStream" aria-live="polite">
    {boundedMessages(messages).map((message) => (
      <article className={`message ${message.role}`} key={message.id}>
        <div className="messageText">{message.role === 'jarvis' && <i aria-hidden="true" />}{message.text}</div>
        <time>{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
      </article>
    ))}
  </section>;
}
