/**
 * J.A.R.V.I.S. v3.0 — useFocusTrap
 * DRY a11y primitive for modal surfaces.
 *
 *  - Guards on `active` → no stale listeners when the surface is closed.
 *  - Optionally traps Tab focus within the container.
 *  - Optionally closes on Esc (stopPropagation so a non-modal panel's Esc
 *    does not also dismiss a modal layered above it).
 *  - Restores focus to the previously active element on deactivate.
 *  - Scroll-locks <body> while active, restoring the prior overflow value.
 */

import { useEffect, useRef } from 'react';

interface FocusTrapOptions {
  onEscape?: () => void;
  scrollLock?: boolean;
  trap?: boolean;
}

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function visibleFocusables(node: HTMLElement): HTMLElement[] {
  return Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.offsetParent !== null,
  );
}

export function useFocusTrap<T extends HTMLElement>(
  active: boolean,
  options: FocusTrapOptions = {},
) {
  const { onEscape, scrollLock = false, trap = true } = options;
  const ref = useRef<T>(null);
  const escapeRef = useRef(onEscape);
  escapeRef.current = onEscape;

  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;

    const prevFocus = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    if (scrollLock) document.body.style.overflow = 'hidden';

    if (trap) {
      const first = visibleFocusables(node)[0];
      (first ?? node).focus();
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (escapeRef.current) {
          e.preventDefault();
          e.stopPropagation();
          escapeRef.current();
        }
        return;
      }
      if (!trap || e.key !== 'Tab') return;
      const els = visibleFocusables(node);
      if (!els.length) return;
      const first = els[0];
      const last = els[els.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown, false);
    return () => {
      document.removeEventListener('keydown', onKeyDown, false);
      if (scrollLock) document.body.style.overflow = prevOverflow;
      prevFocus?.focus?.();
    };
  }, [active, scrollLock, trap]);

  return ref;
}
