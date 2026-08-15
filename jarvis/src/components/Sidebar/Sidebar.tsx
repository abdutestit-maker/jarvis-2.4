/**
 * J.A.R.V.I.S. v3.0 — Sidebar
 * Collapsible left navigation. Real data only:
 *   New session / Search / Pinned / Recent / Settings / User profile.
 * No fabricated sections.
 */

import { useMemo, useState } from 'react';
import {
  Plus, Search, Pin, Clock, Settings, PanelLeftClose,
  MoreHorizontal, Pencil, Trash2,
} from 'lucide-react';
import { useUIState } from '@/hooks/useUIState';
import { useSessions } from '@/stores/sessionStore';
import { useTheme } from '@/stores/themeStore';
import { CoreSymbol } from '@/components/CoreSymbol/CoreSymbol';
import type { Session } from '@/types';
import styles from './Sidebar.module.css';

function timeAgo(ts: number): string {
  const d = Date.now() - ts;
  const m = Math.floor(d / 60000);
  if (m < 1) return 'now';
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export function Sidebar() {
  const { dispatch, entityState, streamingEventId } = useUIState();
  const { sessions, activeId, newSession, select, togglePin, rename, remove } = useSessions();
  const { profile } = useTheme();
  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const isStreaming = streamingEventId != null;

  const { pinned, recent } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? sessions.filter((s) => s.title.toLowerCase().includes(q))
      : sessions;
    return {
      pinned: filtered.filter((s) => s.pinned),
      recent: filtered.filter((s) => !s.pinned),
    };
  }, [sessions, query]);

  const commitRename = (s: Session) => {
    rename(s.id, draft);
    setEditingId(null);
  };

  return (
    <aside className={styles.sidebar} aria-label="Sessions">
      <div className={styles.head}>
        <div className={styles.brand}>
          <CoreSymbol state={entityState} size={20} />
          <span className={styles.brandWord}>J.A.R.V.I.S.</span>
        </div>
        <button
          className={styles.iconBtn}
          onClick={() => dispatch({ type: 'SET_SIDEBAR_OPEN', payload: false })}
          aria-label="Свернуть панель"
          title="Свернуть"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      <div className={styles.search}>
        <Search size={15} className={styles.searchIcon} aria-hidden="true" />
        <input
          className={styles.searchInput}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск сессий"
          aria-label="Поиск сессий"
        />
      </div>

      <button
        className={styles.newBtn}
        onClick={newSession}
        disabled={isStreaming}
        aria-disabled={isStreaming}
        title={isStreaming ? 'Дождитесь завершения ответа' : undefined}
      >
        <Plus size={16} />
        <span>Новая сессия</span>
      </button>

      <nav className={styles.scroll} aria-label="Список сессий">
        {pinned.length > 0 && <SectionLabel icon={<Pin size={12} />} text="Закреплённые" />}
        {pinned.map((s) => (
          <SessionRow
            key={s.id}
            s={s}
            active={s.id === activeId}
            editing={editingId === s.id}
            draft={draft}
            setDraft={setDraft}
            onSelect={() => select(s.id)}
            onTogglePin={() => togglePin(s.id)}
            onEdit={() => { setEditingId(s.id); setDraft(s.title); }}
            onCommit={() => commitRename(s)}
            onCancel={() => setEditingId(null)}
            onRemove={() => remove(s.id)}
            disabled={isStreaming}
          />
        ))}

        <SectionLabel icon={<Clock size={12} />} text="Недавние" />
        {recent.map((s) => (
          <SessionRow
            key={s.id}
            s={s}
            active={s.id === activeId}
            editing={editingId === s.id}
            draft={draft}
            setDraft={setDraft}
            onSelect={() => select(s.id)}
            onTogglePin={() => togglePin(s.id)}
            onEdit={() => { setEditingId(s.id); setDraft(s.title); }}
            onCommit={() => commitRename(s)}
            onCancel={() => setEditingId(null)}
            onRemove={() => remove(s.id)}
            disabled={isStreaming}
          />
        ))}

        {sessions.length === 0 && (
          <div className={styles.empty}>Нет сессий</div>
        )}
      </nav>

      <div className={styles.footer}>
        <button
          className={styles.footerBtn}
          onClick={() => dispatch({ type: 'SET_SETTINGS_OPEN', payload: true })}
        >
          <Settings size={16} />
          <span>Настройки</span>
        </button>

        <div className={styles.profile}>
          <div className={styles.avatar}>{profile?.name?.[0]?.toUpperCase() ?? 'J'}</div>
          <div className={styles.profileMeta}>
            <span className={styles.profileName}>{profile?.name ?? 'Гость'}</span>
            <span className={styles.profileSub}>{profile ? `обращение: ${profile.honorific}` : 'не настроено'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function SectionLabel({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className={styles.section}>
      {icon}
      <span>{text}</span>
    </div>
  );
}

interface RowProps {
  s: Session;
  active: boolean;
  editing: boolean;
  draft: string;
  setDraft: (v: string) => void;
  onSelect: () => void;
  onTogglePin: () => void;
  onEdit: () => void;
  onCommit: () => void;
  onCancel: () => void;
  onRemove: () => void;
  disabled: boolean;
}

function SessionRow(props: RowProps) {
  const { s, active, editing, draft, setDraft, onSelect, onTogglePin, onEdit, onCommit, onCancel, onRemove, disabled } = props;
  const [menu, setMenu] = useState(false);

  if (editing) {
    return (
      <div className={`${styles.row} ${styles.rowActive}`}>
        <input
          className={styles.rename}
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onCommit();
            if (e.key === 'Escape') onCancel();
          }}
          onBlur={onCommit}
          aria-label="Переименовать сессию"
        />
      </div>
    );
  }

  return (
    <div
      className={`${styles.row} ${active ? styles.rowActive : ''} ${disabled ? styles.rowDisabled : ''}`}
      onClick={() => { if (disabled) return; onSelect(); }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => { if (disabled) return; if (e.key === 'Enter') onSelect(); }}
      aria-disabled={disabled || undefined}
      aria-current={active ? 'true' : undefined}
    >
      <div className={styles.rowMain}>
        <span className={styles.rowTitle}>{s.title}</span>
        <span className={styles.rowTime}>{timeAgo(s.updatedAt)}</span>
      </div>

      <div className={styles.rowActions} onClick={(e) => e.stopPropagation()}>
        <button
          className={`${styles.rowBtn} ${s.pinned ? styles.rowBtnOn : ''}`}
          onClick={onTogglePin}
          aria-label={s.pinned ? 'Открепить' : 'Закрепить'}
          title={s.pinned ? 'Открепить' : 'Закрепить'}
        >
          <Pin size={13} />
        </button>
        <div className={styles.menuWrap}>
          <button
            className={styles.rowBtn}
            onClick={() => setMenu((v) => !v)}
            aria-label="Действия"
            title="Действия"
          >
            <MoreHorizontal size={13} />
          </button>
          {menu && (
            <div className={styles.menu} role="menu">
              <button role="menuitem" onClick={() => { setMenu(false); onEdit(); }}>
                <Pencil size={13} /> Переименовать
              </button>
              <button role="menuitem" className={styles.menuDanger} onClick={() => { setMenu(false); onRemove(); }}>
                <Trash2 size={13} /> Удалить
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
