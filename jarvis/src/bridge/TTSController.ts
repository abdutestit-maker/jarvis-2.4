/** Browser UI mirror of backend TTS state; audio remains owned by Python/Piper. */
export class TTSController {
  private speaking = false;
  start(): void { this.speaking = true; }
  interrupt(): void { this.speaking = false; }
  finish(): void { this.speaking = false; }
  get active(): boolean { return this.speaking; }
}
