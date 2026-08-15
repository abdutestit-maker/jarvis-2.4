import assert from 'node:assert/strict';

import { mapSocketEnvelope } from '../src/integrations/wsProtocol.ts';

const now = 1_725_000_000_000;

assert.deepEqual(
  mapSocketEnvelope({ type: 'state', state: 'thinking' }, now),
  [{ type: 'state:thinking', payload: null, timestamp: now }],
);

assert.deepEqual(
  mapSocketEnvelope({
    type: 'event',
    event: {
      type: 'event:jarvis:end',
      payload: { id: 'answer-1', kind: 'jarvis', content: 'Реальный ответ' },
      timestamp: 42,
    },
  }, now),
  [{
    type: 'event:jarvis:end',
    payload: { id: 'answer-1', kind: 'jarvis', content: 'Реальный ответ' },
    timestamp: 42,
  }],
);

assert.deepEqual(
  mapSocketEnvelope({
    type: 'confirmation_required',
    confirmation_id: 'confirm-1',
    prompt: 'Подтвердите действие',
    tool: 'filesystem.delete',
    risk: { level: 'high' },
  }, now),
  [{
    type: 'confirmation:required',
    payload: {
      confirmationId: 'confirm-1',
      prompt: 'Подтвердите действие',
      tool: 'filesystem.delete',
      risk: { level: 'high' },
    },
    timestamp: now,
  }],
);

assert.deepEqual(mapSocketEnvelope({ type: 'unknown' }, now), []);

console.log('wsProtocol: 4 assertions passed');
