import { useEffect, useRef, useState } from 'react';

export function InputLine({ onSend, placeholder = 'Скажи мне...', autoFocus = false }: { onSend: (text: string) => void; placeholder?: string; autoFocus?: boolean }) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { if (autoFocus) ref.current?.focus(); }, [autoFocus]);
  return <form className="inputLine" onSubmit={(event) => { event.preventDefault(); const text = value.trim(); if (text) { onSend(text); setValue(''); } }}>
    <input ref={ref} value={value} onChange={(event) => setValue(event.target.value)} placeholder={placeholder} aria-label={placeholder} />
  </form>;
}
