# main.py - PosturePro Fall Detection System
# Run: python main.py


import cv2
import sys
import time
import signal
import platform

from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import drawing_styles as mp_drawing_styles
from mediapipe.python.solutions import pose as mp_pose

from config import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    FPS_TARGET,
    MP_MODEL_COMPLEXITY,
    MP_MIN_DETECTION_CONFIDENCE,
    MP_MIN_TRACKING_CONFIDENCE,
    FALL_CONFIRM_SECONDS,
    SOS_TIMER_SECONDS,
    KEYPOINT_VISIBILITY_THRESHOLD,
)
from pose_detector import PoseDetector
from fall_logic import FallStateMachine, State
from alert_manager import AlertManager
from voice_listener import VoiceListener
from logger import log

_pose_draw = mp_pose.Pose(
    model_complexity=MP_MODEL_COMPLEXITY,
    min_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
    min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
    enable_segmentation=False,
    smooth_landmarks=True,
)

STATE_COLORS = {
    "IDLE":          (130, 130, 130),
    "MONITORING":    (0,   210, 0  ),
    "FALL_DETECTED": (0,   140, 255),
    "SOS_SENT":      (0,   0,   255),
}
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0  )
RED    = (0,   0,   220)
ORANGE = (0,   140, 255)
GREEN  = (0,   210, 0  )

_running = True

def _signal_handler(sig, frame):
    global _running
    log.info("Shutting down...")
    _running = False

signal.signal(signal.SIGINT, _signal_handler)


def draw_text_bg(img, text, pos, scale=0.6, color=WHITE, thickness=1):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), bl = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    cv2.rectangle(img, (x - 2, y - th - 4), (x + tw + 4, y + bl + 2), BLACK, -1)
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def draw_fall_box(frame, kp):
    points = []
    for idx in [0, 11, 12, 23, 24, 25, 26, 27, 28]:
        try:
            lm = kp.raw[idx]
            if lm.visibility >= KEYPOINT_VISIBILITY_THRESHOLD:
                px = int(lm.x * frame.shape[1])
                py = int(lm.y * frame.shape[0])
                points.append((px, py))
        except Exception:
            pass

    if len(points) < 2:
        return

    xs  = [p[0] for p in points]
    ys  = [p[1] for p in points]
    pad = 20
    x1  = max(0, min(xs) - pad)
    y1  = max(0, min(ys) - pad)
    x2  = min(frame.shape[1], max(xs) + pad)
    y2  = min(frame.shape[0], max(ys) + pad)

    cv2.rectangle(frame, (x1, y1), (x2, y2), RED, 2)
    font  = cv2.FONT_HERSHEY_SIMPLEX
    (lw, lh), _ = cv2.getTextSize("FALL", font, 0.9, 2)
    lx = x1
    ly = max(lh + 8, y1 - 6)
    cv2.rectangle(frame, (lx - 2, ly - lh - 4), (lx + lw + 4, ly + 4), RED, -1)
    cv2.putText(frame, "FALL", (lx, ly), font, 0.9, WHITE, 2, cv2.LINE_AA)


def draw_sos_overlay(frame):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 180), -1)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize("SOS SENT", font, 1.4, 3)
    cx = (frame.shape[1] - tw) // 2
    cy = frame.shape[0] // 2
    cv2.putText(frame, "SOS SENT", (cx, cy), font, 1.4, WHITE, 3, cv2.LINE_AA)


def draw_timer_bar(frame, elapsed, total, color, label):
    bh    = 18
    by    = frame.shape[0] - bh - 2
    bw    = frame.shape[1]
    ratio = min(1.0, elapsed / total)
    cv2.rectangle(frame, (0, by), (bw, by + bh), (40, 40, 40), -1)
    fill_w = int(bw * ratio)
    if fill_w > 0:
        cv2.rectangle(frame, (0, by), (fill_w, by + bh), color, -1)
    cv2.putText(frame, f"{label}: {int(ratio*100)}%  ({elapsed:.0f}s/{total}s)",
                (6, by + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1, cv2.LINE_AA)


def main():
    global _running

    log.info("PosturePro Fall Detection - Starting")

    if platform.system() == "Windows":
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          FPS_TARGET)

    if not cap.isOpened():
        log.error(f"Cannot open camera {CAMERA_INDEX}")
        sys.exit(1)

    log.info(f"Camera opened: {int(cap.get(3))}x{int(cap.get(4))}")

    pose_detector      = PoseDetector()
    alert_manager      = AlertManager()
    voice_listener_ref = [None]

    state_machine = FallStateMachine(
        on_fall_confirmed = lambda: _on_fall_confirmed(alert_manager, voice_listener_ref),
        on_sos_trigger    = lambda reason: _on_sos_trigger(alert_manager, reason),
        on_recover        = lambda: _on_recover(alert_manager, voice_listener_ref),
        on_sos_cancel     = lambda: _on_sos_cancel(alert_manager, voice_listener_ref),
    )

    voice_listener        = VoiceListener(state_machine)
    voice_listener_ref[0] = voice_listener
    voice_listener.start()

    alert_manager.set_voice_window_callbacks(
        on_silence_start = lambda: voice_listener.set_active(True),
        on_silence_end   = lambda: voice_listener.set_active(False),
    )

    win = "PosturePro Fall Detection"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    frame_count = 0
    fps_timer   = time.time()
    fps_val     = 0.0
    frame_skip  = 0

    while _running:
        ret, frame = cap.read()
        if not ret:
            frame_skip += 1
            if frame_skip > 30:
                log.error("Camera read failed - exiting")
                break
            time.sleep(0.05)
            continue
        frame_skip  = 0
        frame_count += 1

        if frame_count % 60 == 0:
            fps_val   = 60 / max(0.001, time.time() - fps_timer)
            fps_timer = time.time()

        kp            = pose_detector.process(frame)
        current_state = state_machine.update(kp)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = _pose_draw.process(rgb)
        rgb.flags.writeable = True

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style(),
            )

        if current_state in (State.FALL_DETECTED, State.SOS_SENT) and kp is not None:
            draw_fall_box(frame, kp)

        if current_state == State.SOS_SENT:
            draw_sos_overlay(frame)

        if current_state == State.FALL_DETECTED and state_machine._beep_start_time:
            draw_timer_bar(frame, time.time() - state_machine._beep_start_time,
                           SOS_TIMER_SECONDS, ORANGE, "SOS in")
        elif current_state == State.MONITORING and state_machine._fall_start_time:
            draw_timer_bar(frame, time.time() - state_machine._fall_start_time,
                           FALL_CONFIRM_SECONDS, (0, 200, 200), "Confirming fall")

        state_name  = current_state.name
        state_color = STATE_COLORS.get(state_name, WHITE)
        cv2.rectangle(frame, (0, 0), (FRAME_WIDTH, 34), (20, 20, 20), -1)
        draw_text_bg(frame, f"STATE: {state_name.replace('_', ' ')}", (8, 24),
                     scale=0.75, color=state_color, thickness=2)
        draw_text_bg(frame, f"FPS: {fps_val:.1f}", (FRAME_WIDTH - 95, 24),
                     scale=0.6, color=WHITE)

        if voice_listener and voice_listener.is_available:
            mic_on  = voice_listener._active
            mic_txt = "MIC: ON" if mic_on else "MIC: OFF"
            mic_col = GREEN if mic_on else (100, 100, 100)
            draw_text_bg(frame, mic_txt, (FRAME_WIDTH - 95, 55), scale=0.55, color=mic_col)

        try:
            rect = cv2.getWindowImageRect(win)
            if rect[2] > 0 and rect[3] > 0:
                frame = cv2.resize(frame, (rect[2], rect[3]))
        except Exception:
            pass

        cv2.imshow(win, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            log.info("Q pressed - shutting down")
            break

        time.sleep(max(0, (1.0 / FPS_TARGET) - 0.005))

    log.info("Releasing resources...")
    cap.release()
    pose_detector.release()
    _pose_draw.close()
    alert_manager.cleanup()
    if voice_listener:
        voice_listener.stop()
    cv2.destroyAllWindows()
    log.info("System stopped.")


def _on_fall_confirmed(alert_manager, vl_ref):
    alert_manager.start_beep()

def _on_sos_trigger(alert_manager, reason):
    alert_manager.send_sos(reason)

def _on_recover(alert_manager, vl_ref):
    alert_manager.stop_beep()
    vl = vl_ref[0]
    if vl:
        vl.set_active(False)
    log.info("Recovery - beep OFF, mic OFF")

def _on_sos_cancel(alert_manager, vl_ref):
    alert_manager.stop_beep()
    alert_manager.send_sos_cancel()
    vl = vl_ref[0]
    if vl:
        vl.set_active(False)
    log.info("SOS cancelled - beep OFF, cancel SMS sent")


if __name__ == "__main__":
    main()
