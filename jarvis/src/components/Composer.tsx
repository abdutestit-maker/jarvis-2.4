/**
 * J.A.R.V.I.S. v3.0 — Composer
 * Refit of the original CommandInput. Premium, multiline, glass, anchored bottom.
 * Preserves ALL prior behavior: Enter/Shift+Enter, drag-drop, paste-attach,
 * Esc clear, file chips. Adds an optional Stop affordance (shown while busy,
 * only if a real backend interrupt exists — no fake control).
 */

import { useRef, useState, useCallback, useEffect, type KeyboardEvent, type DragEvent, type ChangeEvent, type CompositionEvent, type ClipboardEvent } from 'react';
import { Send, Paperclip, Square, X, Upload, Loader2 } from 'lucide-react';
import { useUIState } from '@/hooks/useUIState';
import type { AttachedFile } from '@/types';
import styles from './Composer.module.css';

interface Props {
  onSend: (text: string, files: AttachedFile[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({ onSend, onStop, disabled = false, placeholder = 'Какова наша цель?' }: Props) {
  const { entityState } = useUIState();
  const taRef = useRef<HTMLTextAreaElement>(null);
  const [value, setValue] = useState('');
  const [files, setFiles] = useState<AttachedFile[]>([]);
  const [composing, setComposing] = useState(false);
  const [dragging, setDragging] = useState(false);

  const busy = entityState === 'streaming' || entityState === 'thinking' || entityState === 'executing';
  const canSend = (value.trim().length > 0 || files.length > 0) && !disabled && !busy;

  const resize = useCallback(() => {
    const ta = taRef.current; if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 220) + 'px';
  }, []);
  useEffect(resize, [value, resize]);

  const send = useCallback(() => {
    if (!canSend) return;
    onSend(value.trim(), files);
    setValue(''); setFiles([]);
    if (taRef.current) taRef.current.style.height = 'auto';
  }, [canSend, value, files, onSend]);

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !composing) { e.preventDefault(); send(); }
    if (e.key === 'Escape') { setValue(''); setFiles([]); }
  };

  const addFiles = useCallback((list: FileList) => {
    const next: AttachedFile[] = Array.from(list).map((f) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      name: f.name, size: f.size, type: f.type || 'application/octet-stream',
    }));
    setFiles((p) => [...p, ...next]);
  }, []);

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const fmt = (b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`;

  return (
    <div
      className={`${styles.wrap} ${dragging ? styles.dragging : ''} glass-input`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
      onDrop={onDrop}
    >
      {files.length > 0 && (
        <div className={styles.chips}>
          {files.map((f) => (
            <div key={f.id} className={styles.chip}>
              <Upload size={13} />
              <span className={styles.cName}>{f.name}</span>
              <span className={styles.cSize}>{fmt(f.size)}</span>
              <button className={styles.cX} onClick={() => setFiles((p) => p.filter((x) => x.id !== f.id))} aria-label="Удалить">
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className={styles.row}>
        <textarea
          ref={taRef}
          className={styles.ta}
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          spellCheck={false}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => { if (!composing) setValue(e.target.value); }}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={(e: CompositionEvent<HTMLTextAreaElement>) => { setComposing(false); setValue(e.currentTarget.value); }}
          onKeyDown={onKey}
          onPaste={(e: ClipboardEvent<HTMLTextAreaElement>) => { if (e.clipboardData.files.length) { e.preventDefault(); addFiles(e.clipboardData.files); } }}
          aria-label="Команда для J.A.R.V.I.S."
        />

        <div className={styles.actions}>
          <label className={styles.iconBtn} title="Прикрепить файл" aria-label="Прикрепить файл">
            <Paperclip size={18} />
            <input
              type="file"
              multiple
              hidden
              onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.currentTarget.value = ''; }}
            />
          </label>
          {busy && onStop ? (
            <button className={`${styles.send} ${styles.stop}`} onClick={onStop} aria-label="Остановить">
              <Square size={16} />
            </button>
          ) : (
            <button className={`${styles.send} ${canSend ? '' : styles.sendOff}`} onClick={send} disabled={!canSend} aria-label={busy ? 'J.A.R.V.I.S. работает' : 'Отправить'}>
              {busy ? <Loader2 size={18} className={styles.spin} /> : <Send size={18} />}
            </button>
          )}
        </div>
      </div>

      <div className={styles.hint}>
        <kbd>Enter</kbd> отправить · <kbd>Shift+Enter</kbd> новая строка · <kbd>Esc</kbd> очистить · перетащите файлы
      </div>
    </div>
  );
}
