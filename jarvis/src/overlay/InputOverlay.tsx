import { useEffect, useRef, useState } from 'react';

export function InputOverlay({ onSend, onClose }: { onSend: (text: string) => void; onClose: () => void }) {
  const [value, setValue] = useState(''); const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  useEffect(() => { const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); }; window.addEventListener('keydown', escape); return () => window.removeEventListener('keydown', escape); }, [onClose]);
  return <form className="overlayInput" onSubmit={(event) => { event.preventDefault(); const text = value.trim(); if (text) onSend(text); }}><input ref={ref} value={value} onChange={(event) => setValue(event.target.value)} placeholder="Скажи мне..." aria-label="Команда для JARVIS" /></form>;
}
