/**
 * J.A.R.V.I.S. v3.0 — Lightweight Markdown renderer (dependency-free).
 *
 * Renders a safe subset of markdown to DOM:
 *   - headings (# .. ####)
 *   - bold **x**, italic *x*, inline code `x`
 *   - fenced code blocks ```lang\n...\n```
 *   - unordered lists (- / *) and ordered lists (1.)
 *   - links [t](url) — opened safely
 *   - paragraphs / line breaks
 *
 * No external dependencies; no dangerouslySetInnerHTML. Code blocks get a
 * hover "copy" button (no heavy syntax-highlight engine — performance first).
 */

import { useState, type ReactNode } from 'react';
import { Copy, Check } from 'lucide-react';
import styles from './Markdown.module.css';

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* noop */ }
  };
  return (
    <div className={styles.codeWrap}>
      <button className={styles.copy} onClick={copy} aria-label="Копировать код">
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <pre className={styles.code}><code>{code}</code></pre>
    </div>
  );
}

function renderInline(text: string, keyBase: string): ReactNode[] {
  // Tokenize on inline code first, then bold/italic/links.
  const out: ReactNode[] = [];
  const parts = text.split(/(`[^`]+`)/g);
  parts.forEach((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      out.push(<code key={`${keyBase}-ic-${i}`} className={styles.inlineCode}>{part.slice(1, -1)}</code>);
      return;
    }
    // links
    const linkRe = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
    let m: RegExpExecArray | null;
    let idx = 0;
    const pieces: ReactNode[] = [];
    // split/exec interleave
    let last = 0;
    linkRe.lastIndex = 0;
    while ((m = linkRe.exec(part))) {
      if (m.index > last) pieces.push(...styleEmphasis(part.slice(last, m.index), `${keyBase}-t-${i}-${idx++}`));
      pieces.push(
        <a key={`${keyBase}-l-${i}-${idx++}`} href={m[2]} target="_blank" rel="noopener noreferrer" className={styles.link}>{m[1]}</a>
      );
      last = m.index + m[0].length;
    }
    if (last < part.length) pieces.push(...styleEmphasis(part.slice(last), `${keyBase}-t-${i}-${idx++}`));
    out.push(...pieces);
  });
  return out;
}

function styleEmphasis(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  // bold then italic
  const segs = text.split(/(\*\*[^*]+\*\*)/g);
  segs.forEach((seg, i) => {
    if (seg.startsWith('**') && seg.endsWith('**')) {
      out.push(<strong key={`${keyBase}-b-${i}`}>{styleItalic(seg.slice(2, -2), `${keyBase}-bi-${i}`)}</strong>);
      return;
    }
    out.push(...styleItalic(seg, `${keyBase}-i-${i}`));
  });
  return out;
}
function styleItalic(text: string, keyBase: string): ReactNode[] {
  const segs = text.split(/(\*[^*]+\*)/g);
  return segs.map((seg, i) =>
    seg.startsWith('*') && seg.endsWith('*')
      ? <em key={`${keyBase}-e-${i}`}>{seg.slice(1, -1)}</em>
      : <span key={`${keyBase}-s-${i}`}>{seg}</span>
  );
}

interface Block { type: 'p' | 'h' | 'ul' | 'ol' | 'code'; text?: string; items?: string[]; level?: number; }

export function Markdown({ text }: { text: string }) {
  const blocks: Block[] = [];
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === '') { i++; continue; }
    // fenced code
    if (line.trim().startsWith('```')) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) { buf.push(lines[i]); i++; }
      i++; // skip closing ```
      blocks.push({ type: 'code', text: buf.join('\n') });
      continue;
    }
    // heading
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) { blocks.push({ type: 'h', level: h[1].length, text: h[2] }); i++; continue; }
    // unordered list
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^[-*]\s+/, '')); i++; }
      blocks.push({ type: 'ul', items });
      continue;
    }
    // ordered list
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) { items.push(lines[i].replace(/^\d+\.\s+/, '')); i++; }
      blocks.push({ type: 'ol', items });
      continue;
    }
    // paragraph (collect until blank / block start)
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() !== '' &&
      !lines[i].trim().startsWith('```') && !/^#{1,4}\s+/.test(lines[i]) &&
      !/^[-*]\s+/.test(lines[i]) && !/^\d+\.\s+/.test(lines[i])) {
      para.push(lines[i]); i++;
    }
    blocks.push({ type: 'p', text: para.join(' ') });
  }

  return (
    <div className={styles.md}>
      {blocks.map((b, i) => {
        if (b.type === 'code') return <CodeBlock key={i} code={b.text ?? ''} />;
        if (b.type === 'h') return <p key={i} className={`${styles.h} ${styles[`h${b.level}` as keyof typeof styles] ?? ''}`}>{renderInline(b.text ?? '', `h-${i}`)}</p>;
        if (b.type === 'ul') return <ul key={i} className={styles.ul}>{b.items?.map((it, j) => <li key={j}>{renderInline(it, `ul-${i}-${j}`)}</li>)}</ul>;
        if (b.type === 'ol') return <ol key={i} className={styles.ol}>{b.items?.map((it, j) => <li key={j}>{renderInline(it, `ol-${i}-${j}`)}</li>)}</ol>;
        return <p key={i} className={styles.p}>{renderInline(b.text ?? '', `p-${i}`)}</p>;
      })}
    </div>
  );
}
