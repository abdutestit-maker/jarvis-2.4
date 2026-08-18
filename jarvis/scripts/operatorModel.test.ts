import assert from 'node:assert/strict';
import type { BackendEvent } from '../src/types/index.ts';
import {
  confirmationFromEvent, createMission, fixtureMission, reduceMission,
} from '../src/operator/model.ts';

const mission = createMission('  Установи   тестовую программу  ', 100);
assert.equal(mission.title, 'Установи тестовую программу');
assert.equal(mission.phase, 'research');
assert.deepEqual(mission.steps.map((step) => step.state), ['active', 'pending', 'pending', 'pending']);

const executing: BackendEvent = { type: 'state:executing', payload: null, timestamp: 101 };
const downloading = reduceMission(mission, executing);
assert.equal(downloading.phase, 'download');
assert.deepEqual(downloading.steps.map((step) => step.state), ['complete', 'active', 'pending', 'pending']);

const unverifiedResult = reduceMission(downloading, {
  type: 'event:result', payload: { success: true, result: 'installer exited with code 0' }, timestamp: 102,
});
assert.equal(unverifiedResult.phase, 'observe');
assert.equal(unverifiedResult.verified, false, 'success/exit code must not become verified UI success');

const verifiedResult = reduceMission(downloading, {
  type: 'event:result', payload: { success: true, verification: { status: 'verified' }, result: 'desired state observed' }, timestamp: 103,
});
assert.equal(verifiedResult.phase, 'verified');
assert.equal(verifiedResult.verified, true);
assert.deepEqual(verifiedResult.steps.map((step) => step.state), ['complete', 'complete', 'complete', 'complete']);

const confirmation = confirmationFromEvent({
  type: 'confirmation:required',
  payload: { confirmationId: 'grant-1', prompt: 'Разрешить установку?', tool: 'software.install', risk: { level: 'high' } },
  timestamp: 104,
});
assert.equal(confirmation?.id, 'grant-1');
assert.equal(confirmation?.risk.level, 'high');

assert.equal(fixtureMission('verified').evidence[0].value, 'VERIFIED');
console.log('operatorModel: 13 assertions passed');
