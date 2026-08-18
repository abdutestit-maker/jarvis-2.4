import { useEffect, useMemo, useRef, useState } from 'react';
import { LogicalSize } from '@tauri-apps/api/dpi';
import { getCurrentWindow } from '@tauri-apps/api/window';
import {
  Check, ChevronRight, Circle, Download, Expand, Globe2, Menu,
  Mic, Minus, Paperclip, Plus, Search, Settings, ShieldCheck,
  Shrink, Square, X,
} from 'lucide-react';
import type { PresenceState } from '@/bridge/StateMachine';
import type { PendingConfirmation } from '@/types';
import type { PresenceMessage } from '@/window/MessageStream';
import type { OperatorMission, UiMode } from './model';

interface Props {
  messages: PresenceMessage[];
  state: PresenceState;
  mode: UiMode;
  mission: OperatorMission | null;
  confirmation: PendingConfirmation | null;
  firstLaunch: boolean;
  onModeChange: (mode: UiMode) => void;
  onSend: (text: string) => void;
  onInterrupt: () => void;
  onVoiceListen: () => void;
  onConfirm: (approved: boolean) => void;
  onNewSession: () => void;
}

const CLOCK = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' });

function useClock(): string {
  const [value, setValue] = useState(() => CLOCK.format(new Date()));
  useEffect(() => {
    const timer = window.setInterval(() => setValue(CLOCK.format(new Date())), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return value;
}

function windowAction(action: 'minimize' | 'close' | 'maximize') {
  try {
    const window = getCurrentWindow();
    if (action === 'minimize') void window.minimize();
    if (action === 'close') void window.close();
    if (action === 'maximize') void window.toggleMaximize();
  } catch { /* browser fixture */ }
}

export function syncWindowMode(mode: UiMode): void {
  try {
    const window = getCurrentWindow();
    const expanded = mode === 'command_center';
    void window.setResizable(expanded);
    void window.setMinSize(new LogicalSize(expanded ? 960 : 360, expanded ? 640 : 520));
    void window.setSize(new LogicalSize(expanded ? 1180 : 360, expanded ? 760 : 520));
    if (expanded) void window.center();
  } catch { /* browser fixture */ }
}

function statusLabel(state: PresenceState, mission: OperatorMission | null, confirmation: PendingConfirmation | null): string {
  if (confirmation) return 'CONFIRMATION';
  if (mission?.verified) return 'VERIFIED';
  if (mission?.phase === 'verify' || mission?.phase === 'observe') return 'VERIFYING';
  if (state === 'thinking') return 'EXECUTING';
  if (state === 'speaking') return 'SPEAKING';
  if (state === 'error') return 'ERROR';
  return 'READY';
}

function SignalCore({ tone, compact = false }: { tone: string; compact?: boolean }) {
  return (
    <div className={`signalCore ${compact ? 'compact' : ''}`} data-tone={tone} aria-hidden="true">
      <span className="signalRing ringOne" />
      <span className="signalRing ringTwo" />
      <span className="signalWave"><i /><i /><i /><i /><i /><i /><i /></span>
    </div>
  );
}

function Composer({ onSend, onInterrupt, onVoiceListen, busy, placeholder }: {
  onSend: (text: string) => void;
  onInterrupt: () => void;
  onVoiceListen: () => void;
  busy: boolean;
  placeholder: string;
}) {
  const [value, setValue] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const submit = () => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue('');
  };
  return (
    <form className="operatorComposer" onSubmit={(event) => { event.preventDefault(); submit(); }}>
      <input ref={input} value={value} onChange={(event) => setValue(event.target.value)} placeholder={placeholder} aria-label="Сообщение для JARVIS" />
      <button type="button" className="iconButton quiet" aria-label="Прикрепить файл"><Paperclip size={18} /></button>
      <button type="button" className="iconButton quiet" onClick={onVoiceListen} aria-label="Голосовой ввод"><Mic size={18} /></button>
      {busy
        ? <button type="button" className="iconButton stop" onClick={onInterrupt} aria-label="Остановить"><Square size={12} fill="currentColor" /></button>
        : <button type="submit" className="sendButton" disabled={!value.trim()} aria-label="Отправить"><ChevronRight size={18} /></button>}
    </form>
  );
}

function MessageTimeline({ messages, compact = false }: { messages: PresenceMessage[]; compact?: boolean }) {
  const visible = messages.slice(compact ? -3 : -5);
  if (visible.length === 0) return (
    <div className="emptyConversation">
      <span>JARVIS готов к работе</span>
      <small>Сформулируйте задачу — интерфейс покажет только подтверждённые действия.</small>
    </div>
  );
  return (
    <div className={`operatorMessages ${compact ? 'compact' : ''}`} role="log" aria-live="polite">
      {visible.map((message) => (
        <article className={`operatorMessage ${message.role}`} key={message.id}>
          <span className="messageMark">{message.role === 'jarvis' ? <SignalCore tone="cyan" compact /> : <Circle size={18} />}</span>
          <div><p>{message.text}</p><time>{CLOCK.format(new Date(message.timestamp))}</time></div>
        </article>
      ))}
    </div>
  );
}

function CompactPresence(props: Props) {
  const clock = useClock();
  const tone = props.confirmation ? 'amber' : props.mission?.verified ? 'lime' : props.state === 'error' ? 'error' : 'cyan';
  const label = statusLabel(props.state, props.mission, props.confirmation);
  return (
    <main className="compactShell">
      <header className="compactTitlebar" data-tauri-drag-region>
        <strong>JARVIS</strong><time>{clock}</time>
        <span className="titleStatusDot" data-tone={tone} />
        <button className="iconButton quiet" onClick={() => props.onModeChange('command_center')} aria-label="Открыть командный центр"><Expand size={17} /></button>
      </header>
      <section className="compactCore">
        <SignalCore tone={tone} />
        <span className="technicalLabel" data-tone={tone}>{label}</span>
      </section>
      <MessageTimeline messages={props.messages} compact />
      {props.mission && props.state === 'thinking' && (
        <button className="expandSuggestion" onClick={() => props.onModeChange('command_center')}>
          <span>Задача выполняется в несколько этапов</span><strong>Открыть центр</strong>
        </button>
      )}
      <Composer
        onSend={props.onSend}
        onInterrupt={props.onInterrupt}
        onVoiceListen={props.onVoiceListen}
        busy={props.state === 'thinking'}
        placeholder={props.firstLaunch ? 'Как тебя зовут?' : 'Сообщение для JARVIS…'}
      />
    </main>
  );
}

function StepRail({ mission }: { mission: OperatorMission }) {
  return (
    <div className="stepRail" aria-label="Этапы миссии">
      {mission.steps.map((step) => (
        <div className="missionStep" data-state={step.state} key={step.id}>
          <span>{step.state === 'complete' ? <Check size={15} /> : step.state === 'failed' ? <X size={15} /> : <i />}</span>
          <strong>{step.label}</strong>
        </div>
      ))}
    </div>
  );
}

function MissionPanel({ mission, confirmation, onConfirm }: {
  mission: OperatorMission;
  confirmation: PendingConfirmation | null;
  onConfirm: (approved: boolean) => void;
}) {
  return (
    <section className="missionPanel" data-phase={mission.phase}>
      <div className="panelHeading"><div><span className="eyebrow">АКТИВНАЯ МИССИЯ</span><h1>{mission.title}</h1></div><span className="missionId">{mission.id.slice(-8)}</span></div>
      <StepRail mission={mission} />
      <div className="activityList">
        {mission.activities.map((activity) => (
          <article className="activityRow" data-status={activity.status} key={activity.id}>
            <span className="activityIcon">{activity.status === 'complete' ? <Check size={15} /> : activity.status === 'failed' ? <X size={15} /> : <Download size={15} />}</span>
            <div><strong>{activity.label}</strong>{activity.detail && <small>{activity.detail}</small>}</div>
            <time>{CLOCK.format(new Date(activity.timestamp))}</time>
          </article>
        ))}
      </div>
      {confirmation && (
        <div className="confirmationBar" role="alert">
          <span className="confirmationIcon">!</span>
          <div><strong>Требуется подтверждение</strong><small>{confirmation.prompt}</small>{confirmation.tool && <code>{confirmation.tool}</code>}</div>
          <button className="confirmPrimary" onClick={() => onConfirm(true)}>ПОДТВЕРДИТЬ</button>
          <button className="confirmSecondary" onClick={() => onConfirm(false)}>ОТМЕНА</button>
        </div>
      )}
      {mission.verified && (
        <div className="verifiedActions">
          <span><ShieldCheck size={18} /> Результат подтверждён</span>
          <button>ПОКАЗАТЬ ДЕТАЛИ</button>
        </div>
      )}
    </section>
  );
}

function EvidenceRail({ mission, confirmation }: { mission: OperatorMission | null; confirmation: PendingConfirmation | null }) {
  const items = mission?.evidence.length ? mission.evidence : [
    { label: 'Состояние', value: mission ? 'Собираю доказательства' : 'Ожидание задачи', tone: 'neutral' as const },
    { label: 'Риск', value: confirmation ? String(confirmation.risk.level ?? 'HIGH').toUpperCase() : 'LOW', tone: confirmation ? 'amber' as const : 'cyan' as const },
    { label: 'Приватность', value: 'Локальный runtime', tone: 'cyan' as const },
  ];
  return (
    <aside className="evidenceRail">
      <span className="railTitle">{mission?.verified ? 'ИТОГ МИССИИ' : confirmation ? 'ДОКАЗАТЕЛЬСТВА' : 'КОНТЕКСТ МИССИИ'}</span>
      {items.slice(0, 3).map((item, index) => (
        <article className="evidenceCard" data-tone={item.tone} key={`${item.label}-${index}`}>
          <span>{index === 0 ? <Globe2 size={20} /> : <ShieldCheck size={20} />}</span>
          <div><small>{item.label}</small><strong>{item.value}</strong></div>
        </article>
      ))}
      {mission && !mission.verified && (
        <article className="nextStepCard"><small>Следующий шаг</small><strong>{mission.phase === 'verify' ? 'Проверить разрешение' : mission.phase === 'install' ? 'Наблюдать установку' : 'Проверить результат'}</strong></article>
      )}
    </aside>
  );
}

function Sidebar({ messages, mission, onNewSession }: { messages: PresenceMessage[]; mission: OperatorMission | null; onNewSession: () => void }) {
  const [query, setQuery] = useState('');
  const [settings, setSettings] = useState(false);
  const sessions = useMemo(() => {
    const commands = messages.filter((message) => message.role === 'user').slice(-6).reverse();
    const rows = commands.map((message) => ({ id: message.id, title: message.text, time: CLOCK.format(new Date(message.timestamp)) }));
    if (mission && rows.length === 0) {
      rows.unshift({ id: mission.id, title: mission.title, time: 'сейчас' });
    }
    return rows.filter((row) => row.title.toLowerCase().includes(query.toLowerCase()));
  }, [messages, mission, query]);
  return (
    <aside className="operatorSidebar">
      <div className="sideBrand"><strong>JARVIS</strong><span>LOCAL OPERATOR</span></div>
      <button className="newSession" onClick={onNewSession}><Plus size={17} /> Новая сессия</button>
      <label className="sessionSearch"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск сессий" /></label>
      <span className="sideSection">НЕДАВНИЕ СЕССИИ</span>
      <div className="sessionList">
        {sessions.map((session, index) => <article className={`sessionRow ${index === 0 ? 'active' : ''}`} key={session.id}><span><SignalCore tone="cyan" compact /></span><div><strong>{session.title}</strong><time>{session.time}</time></div></article>)}
        {sessions.length === 0 && <p className="noSessions">История появится после первой команды.</p>}
      </div>
      <button className="settingsButton" onClick={() => setSettings((value) => !value)}><Settings size={17} /> Настройки</button>
      {settings && <div className="quickSettings"><strong>Интерфейс</strong><span>Obsidian Operator</span><small>Данные и вычисления остаются локальными.</small></div>}
    </aside>
  );
}

function CommandCenter(props: Props) {
  const clock = useClock();
  const tone = props.confirmation ? 'amber' : props.mission?.verified ? 'lime' : props.state === 'error' ? 'error' : 'cyan';
  const label = statusLabel(props.state, props.mission, props.confirmation);
  return (
    <main className="commandShell">
      <Sidebar messages={props.messages} mission={props.mission} onNewSession={props.onNewSession} />
      <section className="operatorMain">
        <header className="operatorTitlebar" data-tauri-drag-region>
          <button className="iconButton quiet mobileMenu" aria-label="Меню"><Menu size={18} /></button>
          <SignalCore tone={tone} compact /><span className="technicalLabel" data-tone={tone}>{label}</span>
          <span className="operatorClock">{clock}</span><span className="titleStatusDot" data-tone={tone} />
          <button className="iconButton quiet" onClick={() => props.onModeChange('presence')} aria-label="Компактный режим"><Shrink size={17} /></button>
          <button className="iconButton quiet" onClick={() => windowAction('minimize')} aria-label="Свернуть"><Minus size={17} /></button>
          <button className="iconButton quiet" onClick={() => windowAction('maximize')} aria-label="Развернуть"><Square size={13} /></button>
          <button className="iconButton quiet closeButton" onClick={() => windowAction('close')} aria-label="Закрыть"><X size={17} /></button>
        </header>
        <div className="operatorContent">
          <MessageTimeline messages={props.messages} />
          {props.mission ? <MissionPanel mission={props.mission} confirmation={props.confirmation} onConfirm={props.onConfirm} /> : (
            <section className="welcomeMission"><SignalCore tone={tone} /><h1>Готов к следующей задаче</h1><p>Диалог остаётся главным. Миссия, инструменты и доказательства появятся только когда они действительно нужны.</p></section>
          )}
        </div>
        <Composer onSend={props.onSend} onInterrupt={props.onInterrupt} onVoiceListen={props.onVoiceListen} busy={props.state === 'thinking'} placeholder={props.firstLaunch ? 'Как тебя зовут?' : 'Сообщение для JARVIS…'} />
      </section>
      <EvidenceRail mission={props.mission} confirmation={props.confirmation} />
    </main>
  );
}

export function OperatorShell(props: Props) {
  useEffect(() => syncWindowMode(props.mode), [props.mode]);
  useEffect(() => {
    const hotkey = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.code === 'Space') {
        event.preventDefault();
        props.onModeChange(props.mode === 'presence' ? 'command_center' : 'presence');
      }
    };
    window.addEventListener('keydown', hotkey);
    return () => window.removeEventListener('keydown', hotkey);
  }, [props]);
  return props.mode === 'presence' ? <CompactPresence {...props} /> : <CommandCenter {...props} />;
}
