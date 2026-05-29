# alert_manager.py - Beep + SOS dispatcher
# Laptop version: uses winsound for beep, simulates SMS in terminal
# Beep pattern: 2s ON / 5s OFF with voice window

import time
import threading
from logger import log

try:
    import RPi.GPIO as GPIO
    ON_RASPBERRY_PI = True
except (ImportError, RuntimeError):
    ON_RASPBERRY_PI = False

from config import (
    BUZZER_GPIO_PIN,
    BUZZER_BEEP_DURATION,
    BUZZER_BEEP_PAUSE,
    EMERGENCY_CONTACTS,
    SOS_MESSAGE,
    SOS_CANCEL_MESSAGE,
)


class AlertManager:
    def __init__(self):
        self._beep_thread      = None
        self._beep_stop_event  = threading.Event()
        self._beep_running     = False
        self._beep_lock        = threading.Lock()
        self._on_silence_start = None
        self._on_silence_end   = None

        if ON_RASPBERRY_PI:
            self._setup_gpio()
            log.info(f"AlertManager: RPi GPIO mode (pin={BUZZER_GPIO_PIN})")
        else:
            log.info("AlertManager: laptop mode (system speaker beep)")

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_GPIO_PIN, GPIO.OUT)
        GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)

    def set_voice_window_callbacks(self, on_silence_start, on_silence_end):
        self._on_silence_start = on_silence_start
        self._on_silence_end   = on_silence_end

    def start_beep(self):
        with self._beep_lock:
            if self._beep_running:
                return
            self._beep_stop_event.clear()
            self._beep_running = True
            self._beep_thread  = threading.Thread(
                target=self._beep_loop, daemon=True, name="BeepThread"
            )
            self._beep_thread.start()
        log.alert("Beep loop STARTED (2s ON / 5s OFF)")

    def stop_beep(self):
        with self._beep_lock:
            if not self._beep_running:
                return
            self._beep_stop_event.set()
            self._beep_running = False
        if ON_RASPBERRY_PI:
            try:
                GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)
            except Exception:
                pass
        if self._beep_thread and self._beep_thread.is_alive():
            self._beep_thread.join(timeout=3)
        log.info("Beep STOPPED")

    def _beep_loop(self):
        while not self._beep_stop_event.is_set():
            self._beep_once()

            if self._beep_stop_event.is_set():
                break

            if self._on_silence_start:
                self._on_silence_start()

            silence_elapsed = 0.0
            while silence_elapsed < BUZZER_BEEP_PAUSE:
                if self._beep_stop_event.is_set():
                    break
                time.sleep(0.1)
                silence_elapsed += 0.1

            if self._beep_stop_event.is_set():
                break

            if self._on_silence_end:
                self._on_silence_end()

    def _beep_once(self):
        if ON_RASPBERRY_PI:
            try:
                GPIO.output(BUZZER_GPIO_PIN, GPIO.HIGH)
                elapsed = 0.0
                while elapsed < BUZZER_BEEP_DURATION:
                    if self._beep_stop_event.is_set():
                        break
                    time.sleep(0.1)
                    elapsed += 0.1
                GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)
            except Exception as e:
                log.error(f"GPIO beep error: {e}")
        else:
            try:
                import os
                os.system(f'powershell -c "[console]::Beep(1000, {int(BUZZER_BEEP_DURATION * 1000)})"')
            except Exception:
                print("\a", end="", flush=True)
                time.sleep(BUZZER_BEEP_DURATION)

    def send_sos(self, reason="Fall detected"):
        log.alert("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log.alert("       SOS TRIGGERED               ")
        log.alert(f"  Reason : {reason}")
        log.alert(f"  Time   : {time.strftime('%Y-%m-%d %H:%M:%S')}")
        log.alert("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log.alert(f"[SIMULATED SMS] -> {SOS_MESSAGE}")
        for i, contact in enumerate(EMERGENCY_CONTACTS, 1):
            if "XXXXXXXXXX" not in contact:
                log.alert(f"  [SMS {i}] -> {contact}: {SOS_MESSAGE}")

    def send_sos_cancel(self):
        log.info("Sending SOS cancellation...")
        log.alert(f"[SIMULATED CANCEL SMS] -> {SOS_CANCEL_MESSAGE}")
        for i, contact in enumerate(EMERGENCY_CONTACTS, 1):
            if "XXXXXXXXXX" not in contact:
                log.alert(f"  [CANCEL SMS {i}] -> {contact}")

    def cleanup(self):
        self.stop_beep()
        if ON_RASPBERRY_PI:
            try:
                GPIO.cleanup()
            except Exception:
                pass
