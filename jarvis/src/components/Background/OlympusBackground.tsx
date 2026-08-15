/**
 * J.A.R.V.I.S. v3.0 — Olympus Background
 * Composes the living background layers (behind all content):
 *   Atmosphere (drifting gradients + vignette + grain)
 *   → OlympusMarble (side-positioned antique bust, swappable asset)
 *   → RimLight (breathing cyan/gold edge)
 */

import { Atmosphere } from './Atmosphere';
import { OlympusMarble } from './OlympusMarble';
import { RimLight } from './RimLight';

export function OlympusBackground() {
  return (
    <>
      <Atmosphere />
      <OlympusMarble />
      <RimLight />
    </>
  );
}
