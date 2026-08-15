/**
 * J.A.R.V.I.S. — преобразование WebSocket-конвертов Python core в UI-события.
 *
 * Модуль намеренно не знает ни о React, ни о Tauri: его можно проверить
 * отдельным Node-скриптом. API-ключи в этот протокол не попадают.
 */

export interface TransportEvent {
  type: string;
  payload: unknown;
  timestamp: number;
}

type SocketEnvelope = {
  type?: unknown;
  state?: unknown;
  event?: unknown;
  confirmation_id?: unknown;
  prompt?: unknown;
  tool?: unknown;
  risk?: unknown;
  vitals?: unknown;
  message?: unknown;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object'
    ? value as Record<string, unknown>
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

/**
 * Преобразует одно JSON-сообщение WS в ноль или несколько UI-событий.
 * Неизвестные конверты игнорируются, а не пробрасываются как фальшивые данные.
 */
export function mapSocketEnvelope(raw: unknown, receivedAt = Date.now()): TransportEvent[] {
  const envelope = asRecord(raw) as SocketEnvelope | null;
  if (!envelope) return [];

  const kind = asString(envelope.type);
  if (kind === 'state') {
    const state = asString(envelope.state);
    return state ? [{ type: `state:${state}`, payload: null, timestamp: receivedAt }] : [];
  }

  if (kind === 'event') {
    const event = asRecord(envelope.event);
    const type = event && asString(event.type);
    if (!event || !type || !type.startsWith('event:')) return [];
    return [{
      type,
      payload: event.payload ?? null,
      timestamp: typeof event.timestamp === 'number' ? event.timestamp : receivedAt,
    }];
  }

  if (kind === 'confirmation_required') {
    const confirmationId = asString(envelope.confirmation_id);
    if (!confirmationId) return [];
    return [{
      type: 'confirmation:required',
      payload: {
        confirmationId,
        prompt: asString(envelope.prompt) ?? '',
        tool: asString(envelope.tool) ?? '',
        risk: asRecord(envelope.risk) ?? {},
      },
      timestamp: receivedAt,
    }];
  }

  if (kind === 'vitals') {
    return [{ type: 'vitals:update', payload: asRecord(envelope.vitals) ?? {}, timestamp: receivedAt }];
  }

  if (kind === 'error') {
    return [{
      type: 'event:system',
      payload: {
        id: `transport-error-${receivedAt}`,
        kind: 'system',
        content: asString(envelope.message) ?? 'Ошибка связи с backend.',
        error: asString(envelope.message) ?? 'Ошибка связи с backend.',
      },
      timestamp: receivedAt,
    }, { type: 'state:error', payload: null, timestamp: receivedAt }];
  }

  return [];
}
