# ─────────────────────────────────────────────
#  features.py  —  Feature extraction pipeline
#
#  Combines Paper 1 (Tran) + Paper 2 (Kibet):
#    - Joint angles (6)
#    - SAR (Shape Aspect Ratio)
#    - Velocity of body center, nose, knees
#
#  Used by fall_logic.py to make fall decisions.
# ─────────────────────────────────────────────

import math
from collections import deque
from typing import Optional, Dict

from pose_detector import PoseKeypoints, compute_joint_angles
from config import VELOCITY_FALL_THRESHOLD
from logger import log


class FeatureExtractor:
    """
    Maintains a short history of keypoint positions and extracts
    velocity + joint angle features each frame.

    Call extract(kp) once per frame to get a feature dict.
    """

    def __init__(self, history_len: int = 4):
        self._body_center_hist  = deque(maxlen=history_len)
        self._nose_hist         = deque(maxlen=history_len)
        self._left_knee_hist    = deque(maxlen=history_len)
        self._right_knee_hist   = deque(maxlen=history_len)

    def extract(self, kp: PoseKeypoints) -> Dict:
        """
        Returns a feature dict with:
          angles           — 6 joint angles (degrees or None)
          sar              — Shape Aspect Ratio (float or None)
          velocity_body    — body center movement (pixels/frame)
          velocity_nose    — nose movement
          velocity_left_knee  / velocity_right_knee
          is_velocity_spike   — True if sudden large movement detected
        """
        # ── Joint angles (Paper 1) ────────────
        angles = compute_joint_angles(kp)

        # ── Velocities (Paper 2) ──────────────
        body_center  = kp.body_center
        nose         = kp.nose
        left_knee    = kp.left_knee
        right_knee   = kp.right_knee

        vel_body       = self._velocity(self._body_center_hist, body_center)
        vel_nose       = self._velocity(self._nose_hist,        nose)
        vel_left_knee  = self._velocity(self._left_knee_hist,   left_knee)
        vel_right_knee = self._velocity(self._right_knee_hist,  right_knee)

        # Update position histories
        if body_center:  self._body_center_hist.append(body_center)
        if nose:         self._nose_hist.append(nose)
        if left_knee:    self._left_knee_hist.append(left_knee)
        if right_knee:   self._right_knee_hist.append(right_knee)

        # Velocity spike = sudden large movement (fall onset)
        is_velocity_spike = any(
            v is not None and v > VELOCITY_FALL_THRESHOLD
            for v in [vel_body, vel_nose]
        )

        return {
            "angles":               angles,
            "sar":                  kp.sar,
            "velocity_body":        vel_body,
            "velocity_nose":        vel_nose,
            "velocity_left_knee":   vel_left_knee,
            "velocity_right_knee":  vel_right_knee,
            "is_velocity_spike":    is_velocity_spike,
        }

    def reset(self):
        """Clear history — call on state transitions."""
        self._body_center_hist.clear()
        self._nose_hist.clear()
        self._left_knee_hist.clear()
        self._right_knee_hist.clear()

    @staticmethod
    def _velocity(history: deque, current_pos) -> Optional[float]:
        """Euclidean distance between current position and previous position."""
        if current_pos is None or len(history) == 0:
            return None
        return math.dist(current_pos, history[-1])
