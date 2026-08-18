export interface AmbientTrigger {
  id: string;
  event: string;
  cooldown_hours: number;
  messages: string[];
}

const MAX_IGNORES = 3;
const SESSION_GAP_MS = 30 * 60 * 1000;

/** Rate limits ambient prompts without requiring a new backend contract. */
export class TriggerEngine {
  private lastAmbient = 0;
  private readonly lastByTrigger = new Map<string, number>();
  private ignores = 0;

  canTrigger(trigger: AmbientTrigger, now = Date.now()): boolean {
    if (this.ignores >= MAX_IGNORES) return false;
    if (now - this.lastAmbient < SESSION_GAP_MS) return false;
    const last = this.lastByTrigger.get(trigger.id) ?? 0;
    return now - last >= trigger.cooldown_hours * 60 * 60 * 1000;
  }

  recordTriggered(trigger: AmbientTrigger, now = Date.now()): void {
    this.lastAmbient = now;
    this.lastByTrigger.set(trigger.id, now);
  }

  recordResponse(): void { this.ignores = 0; }
  recordIgnored(): void { this.ignores += 1; }
  get disabledForSession(): boolean { return this.ignores >= MAX_IGNORES; }
}
