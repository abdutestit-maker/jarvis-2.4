export type PresenceState = 'idle' | 'listening' | 'thinking' | 'executing' | 'speaking' | 'error' | 'proactive';

const ALLOWED: Record<PresenceState, PresenceState[]> = {
  idle: ['listening', 'thinking', 'executing', 'speaking', 'error', 'proactive'],
  listening: ['idle', 'thinking', 'executing', 'speaking', 'error'],
  thinking: ['idle', 'listening', 'executing', 'speaking', 'error'],
  executing: ['idle', 'thinking', 'speaking', 'error'],
  speaking: ['idle', 'listening', 'thinking', 'executing', 'error'],
  error: ['idle', 'listening', 'thinking'],
  proactive: ['idle', 'listening', 'speaking', 'thinking', 'executing'],
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
  if (state === 'listening') return 'listening';
  if (state === 'executing') return 'executing';
  if (state === 'streaming') return 'speaking';
  if (state === 'thinking' || state === 'loading_model') return 'thinking';
  if (state === 'error') return 'error';
  return 'idle';
}
