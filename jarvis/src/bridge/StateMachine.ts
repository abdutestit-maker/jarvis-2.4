export type PresenceState = 'idle' | 'thinking' | 'speaking' | 'error' | 'proactive';

const ALLOWED: Record<PresenceState, PresenceState[]> = {
  idle: ['thinking', 'speaking', 'error', 'proactive'],
  thinking: ['idle', 'speaking', 'error'],
  speaking: ['idle', 'thinking', 'error'],
  error: ['idle', 'thinking'],
  proactive: ['idle', 'speaking', 'thinking'],
};

/** Small, UI-only state machine. It deliberately does not alter the WS protocol. */
export class StateMachine {
  private value: PresenceState = 'idle';

  get state(): PresenceState { return this.value; }

  transition(next: PresenceState): PresenceState {
    if (next === this.value || ALLOWED[this.value].includes(next)) this.value = next;
    return this.value;
  }
}

export function presenceFromTransport(state: string): PresenceState {
  if (state === 'thinking' || state === 'executing' || state === 'streaming') return 'thinking';
  if (state === 'error') return 'error';
  return 'idle';
}
