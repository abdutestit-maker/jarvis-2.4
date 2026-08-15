import assert from 'node:assert/strict';

import type { AttachedFile, BackendEvent } from '../src/types/index.ts';

type Handler<T> = ((event: T) => void) | null;

class FakeSocket {
  static instances: FakeSocket[] = [];

  readyState = 0;
  sent: string[] = [];
  onopen: Handler<Event> = null;
  onclose: Handler<CloseEvent> = null;
  onerror: Handler<Event> = null;
  onmessage: Handler<MessageEvent<string>> = null;
  readonly url: string;

  constructor(url: string) {
    this.url = url;
    FakeSocket.instances.push(this);
  }

  open() {
    this.readyState = 1;
    this.onopen?.({} as Event);
  }

  receive(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent<string>);
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = 3;
    this.onclose?.({} as CloseEvent);
  }
}

const { WebSocketBackend } = await import('../src/integrations/wsBackend.ts');
const transport = new WebSocketBackend('ws://127.0.0.1:8771', (url) => new FakeSocket(url) as unknown as WebSocket);
const events: BackendEvent[] = [];
const unsubscribe = transport.subscribeToEvents((event) => events.push(event));
const socket = FakeSocket.instances[0];
assert.equal(socket.url, 'ws://127.0.0.1:8771');
socket.open();

await transport.sendCommand('проверочная команда', [] as AttachedFile[]);
assert.deepEqual(JSON.parse(socket.sent[0]), { type: 'command', text: 'проверочная команда' });
assert.equal(events[0].type, 'event:command');

socket.receive({ type: 'state', state: 'thinking' });
socket.receive({
  type: 'event',
  event: {
    type: 'event:jarvis:end',
    payload: { id: 'answer-1', kind: 'jarvis', content: 'Реальный ответ' },
    timestamp: 42,
  },
});
socket.receive({
  type: 'confirmation_required',
  confirmation_id: 'confirm-1',
  prompt: 'Подтвердите действие',
  tool: 'filesystem.delete',
  risk: { level: 'high' },
});
assert.deepEqual(events.slice(1).map((event) => event.type), [
  'state:thinking',
  'event:jarvis:end',
  'confirmation:required',
]);

const save = transport.updateCloudSettings({
  provider: 'openrouter',
  base_url: 'https://openrouter.ai/api/v1',
  model: 'openai/gpt-4.1-mini',
  api_key: 'test-key-only',
});
await new Promise<void>((resolve) => setTimeout(resolve, 0));
assert.deepEqual(JSON.parse(socket.sent[1]), {
  type: 'settings:update',
  settings: {
    provider: 'openrouter',
    base_url: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4.1-mini',
    api_key: 'test-key-only',
  },
});
socket.receive({
  type: 'settings:saved',
  ok: true,
  settings: {
    provider: 'openrouter',
    base_url: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4.1-mini',
    has_api_key: true,
    api_key_masked: '••••only',
  },
});
assert.deepEqual(await save, {
  provider: 'openrouter',
  base_url: 'https://openrouter.ai/api/v1',
  model: 'openai/gpt-4.1-mini',
  has_api_key: true,
  api_key_masked: '••••only',
});
assert.equal(JSON.stringify(events).includes('test-key-only'), false);

await transport.answerConfirmation('confirm-1', false);
assert.deepEqual(JSON.parse(socket.sent[2]), {
  type: 'confirm',
  confirmation_id: 'confirm-1',
  approve: false,
});

unsubscribe();
console.log('wsBackend: command, response, confirmation and masked settings passed');
