"""Unified verified setup mission facade.

The Sprint 10 operator already owns the real install/launch/UIA/diff/verify
loop in :class:`OperatorMission`.  ``SetupMission`` gives that pipeline the
canonical name used by the Universal Mind contract without cloning any of the
providers or introducing a second execution authority.
"""

from __future__ import annotations

from .mission import OperatorMission


class SetupMission(OperatorMission):
    """Install, configure, verify and learn one application.

    The inherited ``run`` method is intentionally the single implementation
    of ``understand → trusted_source → verify → install → launch → inspect →
    desired_state_diff → configure → observe → verify → repair → learn``.
    Keeping this as a thin facade preserves additive compatibility with the
    older ``OperatorMission`` name while making the pipeline discoverable to
    the CognitiveKernel and capability graph.
    """

    PIPELINE: tuple[str, ...] = (
        "understand",
        "trusted_source",
        "verify_publisher",
        "verify_hash",
        "verify_signature",
        "install",
        "launch",
        "inspect",
        "desired_state_diff",
        "configure",
        "observe",
        "verify",
        "repair",
        "learn",
    )

    @property
    def pipeline(self) -> tuple[str, ...]:
        """Return the stable phase contract for UI/evidence consumers."""
        return self.PIPELINE


__all__ = ["SetupMission"]
