# ─────────────────────────────────────────────
#  pose_detector.py  —  MediaPipe Pose wrapper
#
#  Phase 4 additions (Paper 1 + Paper 2):
#    - Kalman filter smoothing on all keypoints
#    - SAR  (Shape Aspect Ratio of bounding box)
#    - Joint angles (elbow ×2, hip ×2, knee ×2)
#    - Velocity of body center, nose, knees
# ─────────────────────────────────────────────

import math
from mediapipe.python.solutions import pose as _mp_pose_solutions
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple

from config import (
    MP_MODEL_COMPLEXITY,
    MP_MIN_DETECTION_CONFIDENCE,
    MP_MIN_TRACKING_CONFIDENCE,
    KEYPOINT_VISIBILITY_THRESHOLD,
    SHOW_KEYPOINT_VALUES,
    KALMAN_PROCESS_NOISE,
    KALMAN_MEASUREMENT_NOISE,
)
from logger import log


# ── MediaPipe keypoint indices ────────────────────────────────────────────────
class KP:
    NOSE            = 0
    LEFT_SHOULDER   = 11
    RIGHT_SHOULDER  = 12
    LEFT_ELBOW      = 13
    RIGHT_ELBOW     = 14
    LEFT_WRIST      = 15
    RIGHT_WRIST     = 16
    LEFT_HIP        = 23
    RIGHT_HIP       = 24
    LEFT_KNEE       = 25
    RIGHT_KNEE      = 26
    LEFT_ANKLE      = 27
    RIGHT_ANKLE     = 28


# ── 1D Kalman Filter ─────────────────────────────────────────────────────────
class KalmanFilter1D:
    """
    Lightweight 1-dimensional Kalman filter for smoothing noisy coordinates.
    From Paper 2 (Kibet) — especially important at low FPS on Raspberry Pi.
    """
    def __init__(self, process_noise=KALMAN_PROCESS_NOISE,
                 measurement_noise=KALMAN_MEASUREMENT_NOISE):
        self.Q = process_noise       # process noise
        self.R = measurement_noise   # measurement noise
        self.x = None                # state estimate
        self.P = 1.0                 # estimate uncertainty

    def update(self, measurement: float) -> float:
        if self.x is None:
            self.x = measurement
            return self.x
        # Predict
        self.P = self.P + self.Q
        # Update
        K = self.P / (self.P + self.R)
        self.x = self.x + K * (measurement - self.x)
        self.P = (1 - K) * self.P
        return self.x

    def reset(self):
        self.x = None
        self.P = 1.0


# ── Per-keypoint Kalman smoother ─────────────────────────────────────────────
class KeypointKalmanFilter:
    """Maintains one KalmanFilter1D per coordinate (x, y) per keypoint."""
    def __init__(self, n_keypoints: int = 33):
        self.filters_x = [KalmanFilter1D() for _ in range(n_keypoints)]
        self.filters_y = [KalmanFilter1D() for _ in range(n_keypoints)]

    def smooth(self, idx: int, x: float, y: float) -> Tuple[float, float]:
        sx = self.filters_x[idx].update(x)
        sy = self.filters_y[idx].update(y)
        return sx, sy

    def reset(self):
        for f in self.filters_x:
            f.reset()
        for f in self.filters_y:
            f.reset()


# ── Pose keypoints dataclass ──────────────────────────────────────────────────
@dataclass
class PoseKeypoints:
    """
    Holds smoothed pixel coordinates for all needed keypoints.
    Also carries computed features: SAR, joint angles, velocity.
    """
    # Raw landmark list from MediaPipe
    raw: object
    frame_w: int
    frame_h: int

    # Smoothed coordinates — filled by PoseDetector after Kalman pass
    _smoothed: dict = field(default_factory=dict)

    # Computed features (set by PoseDetector.process)
    sar:            Optional[float] = None   # Shape Aspect Ratio
    left_elbow_angle:  Optional[float] = None
    right_elbow_angle: Optional[float] = None
    left_hip_angle:    Optional[float] = None
    right_hip_angle:   Optional[float] = None
    left_knee_angle:   Optional[float] = None
    right_knee_angle:  Optional[float] = None
    velocity_center:   Optional[float] = None
    velocity_nose:     Optional[float] = None
    velocity_lknee:    Optional[float] = None
    velocity_rknee:    Optional[float] = None

    def _get_raw(self, idx: int):
        """Raw MediaPipe coordinate — used as fallback."""
        lm = self.raw[idx]
        if lm.visibility < KEYPOINT_VISIBILITY_THRESHOLD:
            return None
        return (lm.x * self.frame_w, lm.y * self.frame_h)

    def _get(self, idx: int):
        """Returns smoothed (x, y) or falls back to raw, or None."""
        if idx in self._smoothed:
            return self._smoothed[idx]
        return self._get_raw(idx)

    # ── Keypoint getters ─────────────────────
    @property
    def nose(self):           return self._get(KP.NOSE)
    @property
    def left_shoulder(self):  return self._get(KP.LEFT_SHOULDER)
    @property
    def right_shoulder(self): return self._get(KP.RIGHT_SHOULDER)
    @property
    def left_elbow(self):     return self._get(KP.LEFT_ELBOW)
    @property
    def right_elbow(self):    return self._get(KP.RIGHT_ELBOW)
    @property
    def left_wrist(self):     return self._get(KP.LEFT_WRIST)
    @property
    def right_wrist(self):    return self._get(KP.RIGHT_WRIST)
    @property
    def left_hip(self):       return self._get(KP.LEFT_HIP)
    @property
    def right_hip(self):      return self._get(KP.RIGHT_HIP)
    @property
    def left_knee(self):      return self._get(KP.LEFT_KNEE)
    @property
    def right_knee(self):     return self._get(KP.RIGHT_KNEE)
    @property
    def left_ankle(self):     return self._get(KP.LEFT_ANKLE)
    @property
    def right_ankle(self):    return self._get(KP.RIGHT_ANKLE)

    def midpoint(self, a, b):
        if a is None or b is None:
            return None
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    @property
    def hip_center(self):
        return self.midpoint(self.left_hip, self.right_hip)

    @property
    def shoulder_center(self):
        return self.midpoint(self.left_shoulder, self.right_shoulder)

    @property
    def knee_center(self):
        return self.midpoint(self.left_knee, self.right_knee)

    @property
    def body_center(self):
        """Central point: avg of shoulder midpoint and hip midpoint (Paper 2)."""
        sc = self.shoulder_center
        hc = self.hip_center
        return self.midpoint(sc, hc)


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _angle_between(a, b, c) -> Optional[float]:
    """
    Angle at point B formed by vectors BA and BC. Returns degrees.
    a, b, c are (x, y) tuples.
    """
    if a is None or b is None or c is None:
        return None
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0]*bc[0] + ba[1]*bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return None
    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def compute_torso_angle(kp: PoseKeypoints) -> Optional[float]:
    """
    Angle of torso vector (shoulder_center → hip_center) from horizontal.
    0° = flat, 90° = standing.
    """
    sc = kp.shoulder_center
    hc = kp.hip_center
    if sc is None or hc is None:
        return None
    dx = hc[0] - sc[0]
    dy = hc[1] - sc[1]
    return math.degrees(math.atan2(abs(dy), abs(dx)))


def hips_below_knees(kp: PoseKeypoints) -> Optional[bool]:
    """True if hip_center Y > knee_center Y (image coords, Y down = lower)."""
    hc = kp.hip_center
    kc = kp.knee_center
    if hc is None or kc is None:
        return None
    return hc[1] > kc[1]


def compute_sar(kp: PoseKeypoints) -> Optional[float]:
    """
    Shape Aspect Ratio = bounding box height / width of all visible keypoints.
    Standing: tall narrow box → SAR > 1.5
    Fallen:   wide flat box  → SAR < 0.9
    """
    points = []
    for idx in [KP.NOSE,
                KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER,
                KP.LEFT_HIP,      KP.RIGHT_HIP,
                KP.LEFT_KNEE,     KP.RIGHT_KNEE,
                KP.LEFT_ANKLE,    KP.RIGHT_ANKLE]:
        p = kp._get(idx)
        if p is not None:
            points.append(p)

    if len(points) < 3:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)

    if w < 1:
        return None
    return h / w


def compute_joint_angles(kp: PoseKeypoints) -> dict:
    """
    Computes 6 joint angles from Paper 1 (Tran).
    Returns dict with keys: left_elbow, right_elbow,
                             left_hip, right_hip,
                             left_knee, right_knee
    """
    return {
        "left_elbow":  _angle_between(kp.left_shoulder,  kp.left_elbow,  kp.left_wrist),
        "right_elbow": _angle_between(kp.right_shoulder, kp.right_elbow, kp.right_wrist),
        "left_hip":    _angle_between(kp.left_shoulder,  kp.left_hip,    kp.left_knee),
        "right_hip":   _angle_between(kp.right_shoulder, kp.right_hip,   kp.right_knee),
        "left_knee":   _angle_between(kp.left_hip,       kp.left_knee,   kp.left_ankle),
        "right_knee":  _angle_between(kp.right_hip,      kp.right_knee,  kp.right_ankle),
    }


# ── PoseDetector ──────────────────────────────────────────────────────────────
class PoseDetector:
    def __init__(self):
        self._mp_pose = _mp_pose_solutions
        self._pose = self._mp_pose.Pose(
            model_complexity=MP_MODEL_COMPLEXITY,
            min_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
            enable_segmentation=False,
            smooth_landmarks=True,
        )

        # Kalman filters — one per keypoint per axis
        self._kalman = KeypointKalmanFilter(n_keypoints=33)

        # Previous positions for velocity computation (Paper 2)
        self._prev_center: Optional[Tuple] = None
        self._prev_nose:   Optional[Tuple] = None
        self._prev_lknee:  Optional[Tuple] = None
        self._prev_rknee:  Optional[Tuple] = None

        log.info(f"MediaPipe Pose initialized (complexity={MP_MODEL_COMPLEXITY})")
        log.info("Kalman filter enabled, SAR + joint angles + velocity active")

    def process(self, bgr_frame) -> Optional[PoseKeypoints]:
        import cv2
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._pose.process(rgb)
        rgb.flags.writeable = True

        if not results.pose_landmarks:
            # Reset Kalman and velocity state when person disappears
            self._kalman.reset()
            self._prev_center = None
            self._prev_nose   = None
            self._prev_lknee  = None
            self._prev_rknee  = None
            return None

        h, w = bgr_frame.shape[:2]
        landmarks = results.pose_landmarks.landmark

        # ── Apply Kalman smoothing to all keypoints ───────────────────────────
        smoothed = {}
        for idx in range(33):
            lm = landmarks[idx]
            if lm.visibility >= KEYPOINT_VISIBILITY_THRESHOLD:
                sx, sy = self._kalman.smooth(idx, lm.x * w, lm.y * h)
                smoothed[idx] = (sx, sy)

        kp = PoseKeypoints(raw=landmarks, frame_w=w, frame_h=h, _smoothed=smoothed)

        # ── SAR ───────────────────────────────────────────────────────────────
        kp.sar = compute_sar(kp)

        # ── Joint angles ─────────────────────────────────────────────────────
        angles = compute_joint_angles(kp)
        kp.left_elbow_angle  = angles["left_elbow"]
        kp.right_elbow_angle = angles["right_elbow"]
        kp.left_hip_angle    = angles["left_hip"]
        kp.right_hip_angle   = angles["right_hip"]
        kp.left_knee_angle   = angles["left_knee"]
        kp.right_knee_angle  = angles["right_knee"]

        # ── Velocity (Paper 2) ────────────────────────────────────────────────
        center = kp.body_center
        nose   = kp.nose
        lknee  = kp.left_knee
        rknee  = kp.right_knee

        kp.velocity_center = math.dist(center, self._prev_center) if (center and self._prev_center) else None
        kp.velocity_nose   = math.dist(nose,   self._prev_nose)   if (nose   and self._prev_nose)   else None
        kp.velocity_lknee  = math.dist(lknee,  self._prev_lknee)  if (lknee  and self._prev_lknee)  else None
        kp.velocity_rknee  = math.dist(rknee,  self._prev_rknee)  if (rknee  and self._prev_rknee)  else None

        self._prev_center = center
        self._prev_nose   = nose
        self._prev_lknee  = lknee
        self._prev_rknee  = rknee

        if SHOW_KEYPOINT_VALUES:
            log.debug(
                f"SAR={kp.sar:.2f}  "
                f"hip_angle=({kp.left_hip_angle:.0f}°,{kp.right_hip_angle:.0f}°)  "
                f"knee_angle=({kp.left_knee_angle:.0f}°,{kp.right_knee_angle:.0f}°)  "
                f"vel_center={kp.velocity_center:.1f}px"
                if all(v is not None for v in [kp.sar, kp.left_hip_angle,
                                                kp.right_hip_angle, kp.left_knee_angle,
                                                kp.right_knee_angle, kp.velocity_center])
                else "Some features unavailable this frame"
            )

        return kp

    def release(self):
        self._pose.close()
        log.info("PoseDetector released.")
