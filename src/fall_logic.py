# ─────────────────────────────────────────────
#  fall_logic.py  —  Fall detection state machine
# ─────────────────────────────────────────────

import time
import math
from collections import deque
from enum import Enum, auto
from typing import Optional, Callable

from config import (
    TORSO_ANGLE_THRESHOLD,
    FALL_CONFIRM_SECONDS,
    SOS_TIMER_SECONDS,
    MOTION_PIXEL_THRESHOLD,
    VOTE_WINDOW_SIZE,
    VOTE_THRESHOLD,
    SAR_FALL_THRESHOLD,
    HIP_ANGLE_FALL_THRESHOLD,
    STANDING_NK_BUFFER_PX,
    KEYPOINT_VISIBILITY_THRESHOLD,
)
from pose_detector import PoseKeypoints, compute_torso_angle, hips_below_knees
from logger import log


class State(Enum):
    IDLE          = auto()
    MONITORING    = auto()
    FALL_DETECTED = auto()
    SOS_SENT      = auto()


class FallStateMachine:

    def __init__(
        self,
        on_fall_confirmed: Callable[[], None],
        on_sos_trigger:    Callable[[str], None],
        on_recover:        Callable[[], None],
        on_sos_cancel:     Callable[[], None],
    ):
        self.on_fall_confirmed = on_fall_confirmed
        self.on_sos_trigger    = on_sos_trigger
        self.on_recover        = on_recover
        self.on_sos_cancel     = on_sos_cancel

        self.state: State = State.IDLE

        self._vote_window: deque = deque(maxlen=VOTE_WINDOW_SIZE)
        self._no_person_frames   = 0
        self._fall_start_time: Optional[float] = None
        self._beep_start_time: Optional[float] = None
        self._sos_sent = False
        self.voice_cancel_received = False

        # Recovery: consecutive non-fall frames needed to recover
        self._recovery_frames     = 0
        self._RECOVERY_NEEDED     = 3   # 3 consecutive non-fall frames = recovered 
        self._voice_cancel_cooldown = None  # 1 min cooldown after voice cancel

        log.state(f"State machine initialized → {self.state.name}")

    def update(self, kp: Optional[PoseKeypoints]) -> State:
        prev_state = self.state

        if   self.state == State.IDLE:          self._handle_idle(kp)
        elif self.state == State.MONITORING:    self._handle_monitoring(kp)
        elif self.state == State.FALL_DETECTED: self._handle_fall_detected(kp)
        elif self.state == State.SOS_SENT:      self._handle_sos_sent(kp)

        if self.state != prev_state:
            log.state(f"Transition: {prev_state.name} → {self.state.name}")

        return self.state

    def _handle_idle(self, kp):
        if kp is not None:
            log.info("Person detected → MONITORING")
            self._transition_to_monitoring()

    def _handle_monitoring(self, kp):
        if kp is None:
            self._no_person_frames += 1
            if self._no_person_frames > 30:
                log.info("Person lost → IDLE")
                self.state = State.IDLE
                self._no_person_frames = 0
                self._vote_window.clear()
                self._fall_start_time = None
            return

        self._no_person_frames = 0
        vote = self._classify_fall(kp)
        self._vote_window.append(vote)
        # Check cooldown after voice cancel
        if self._voice_cancel_cooldown is not None:
            if time.time() - self._voice_cancel_cooldown < 60:
                log.debug("Voice cancel cooldown active — ignoring fall")
                return
            else:
                self._voice_cancel_cooldown = None

        fall_votes = sum(self._vote_window)
        log.debug(f"Vote: {'FALL' if vote else 'OK  '} | Window: {fall_votes}/{len(self._vote_window)}")

        if len(self._vote_window) == VOTE_WINDOW_SIZE and fall_votes >= VOTE_THRESHOLD:
            if self._fall_start_time is None:
                self._fall_start_time = time.time()
                log.alert(f"Fall pose detected — confirming for {FALL_CONFIRM_SECONDS}s...")

            elapsed = time.time() - self._fall_start_time
            if elapsed >= FALL_CONFIRM_SECONDS:
                self._transition_to_fall_detected(kp)
        else:
            self._fall_start_time = None

    def _handle_fall_detected(self, kp):
        now     = time.time()
        elapsed = now - self._beep_start_time

        # ── Voice cancel ──────────────────────
        if self.voice_cancel_received:
            log.info(f"Voice cancel at {elapsed:.1f}s → recovery")
            self.voice_cancel_received = False
            self.on_recover()
            self._transition_to_monitoring()
            return

        # ── Recovery: consecutive non-fall frames ─
        if kp is not None:
            is_fall = self._classify_fall(kp)
            if not is_fall:
                self._recovery_frames += 1
                log.debug(f"Recovery frame {self._recovery_frames}/{self._RECOVERY_NEEDED}")
                if self._recovery_frames >= self._RECOVERY_NEEDED:
                    log.info(f"Person recovered at {elapsed:.1f}s → MONITORING")
                    self._recovery_frames = 0
                    self.on_recover()
                    self._transition_to_monitoring()
                    return
            else:
                self._recovery_frames = 0

        # ── SOS timer ─────────────────────────
        if elapsed >= SOS_TIMER_SECONDS and not self._sos_sent:
            self._sos_sent = True
            self.state     = State.SOS_SENT
            log.alert(f"No response for {SOS_TIMER_SECONDS}s → SOS TRIGGERED")
            self.on_sos_trigger("Person fallen and unresponsive for 30 seconds")

    def _handle_sos_sent(self, kp):
        # ── Voice cancel after SOS ────────────
        if self.voice_cancel_received:
            log.info("Voice cancel after SOS → cancel SMS")
            self.voice_cancel_received = False
            self.on_sos_cancel()
            self._transition_to_monitoring()
            return

        # ── Recovery after SOS ────────────────
        if kp is not None:
            is_fall = self._classify_fall(kp)
            if not is_fall:
                self._recovery_frames += 1
                if self._recovery_frames >= self._RECOVERY_NEEDED:
                    log.info("Person recovered after SOS → cancel SMS")
                    self._recovery_frames = 0
                    self.on_sos_cancel()
                    self._transition_to_monitoring()
                    return
            else:
                self._recovery_frames = 0

    def _transition_to_monitoring(self):
        self.state                 = State.MONITORING
        self._no_person_frames     = 0
        self._fall_start_time      = None
        self._beep_start_time      = None
        self._sos_sent             = False
        self._recovery_frames      = 0
        self.voice_cancel_received = False
        self._vote_window.clear()
        self._voice_cancel_cooldown = time.time()

    def _transition_to_fall_detected(self, kp):
        self.state            = State.FALL_DETECTED
        self._beep_start_time = time.time()
        self._sos_sent        = False
        self._recovery_frames = 0
        self._vote_window.clear()
        log.alert(f"FALL CONFIRMED — beep ON, mic ON, {SOS_TIMER_SECONDS}s SOS timer started")
        self.on_fall_confirmed()

    def reset_after_alert(self):
        self._transition_to_monitoring()
        self.state = State.MONITORING

    def _classify_fall(self, kp: PoseKeypoints) -> bool:
        signals = []

        # Signal 1: Torso angle
        angle = compute_torso_angle(kp)
        if angle is not None:
            signals.append(angle < TORSO_ANGLE_THRESHOLD)
            log.debug(f"  Torso: {angle:.1f}° → {'FALL' if angle < TORSO_ANGLE_THRESHOLD else 'OK'}")

        # Signal 2: Hip below knee
        hip_down = hips_below_knees(kp)
        if hip_down is not None:
            signals.append(hip_down)
            log.debug(f"  Hip below knee: {hip_down}")

        # Signal 3: SAR
        if kp.sar is not None:
            sar_fall = kp.sar < SAR_FALL_THRESHOLD
            signals.append(sar_fall)
            log.debug(f"  SAR: {kp.sar:.2f} → {'FALL' if sar_fall else 'OK'}")

        # Signal 4: Hip angle
        hip_angles = [a for a in [kp.left_hip_angle, kp.right_hip_angle] if a is not None]
        if hip_angles:
            avg_hip  = sum(hip_angles) / len(hip_angles)
            hip_fall = avg_hip > HIP_ANGLE_FALL_THRESHOLD
            signals.append(hip_fall)
            log.debug(f"  Hip angle: {avg_hip:.1f}° → {'FALL' if hip_fall else 'OK'}")

        if not signals:
            log.debug("  No signals — defaulting to not-fall")
            return False

        fall_votes = sum(signals)
        result = fall_votes >= 2
        log.debug(f"  Classifier: {fall_votes}/{len(signals)} → {'FALL' if result else 'OK'}")
        return result
