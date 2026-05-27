# alert_manager.py - Handles buzzer beep and GSM SMS alerts

import time
import threading
import serial
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
    GSM_SERIAL_PORT,
    GSM_BAUD_RATE,
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
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUZZER_GPIO_PIN, GPIO.OUT)
            GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)
            log.info(f"Buzzer ready on GPIO {BUZZER_GPIO_PIN}")
        else:
            log.info("Running in simulation mode (not on Pi)")

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
                target=self._beep_loop, daemon=True
            )
            self._beep_thread.start()
        log.alert("Beep started")

    def stop_beep(self):
        with self._beep_lock:
            if not self._beep_running:
                return
            self._beep_stop_event.set()
            self._beep_running = False
        if self._beep_thread and self._beep_thread.is_alive():
            self._beep_thread.join(timeout=3)
        if ON_RASPBERRY_PI:
            try:
                GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)
            except Exception:
                pass
        log.info("Beep stopped")

    def _beep_loop(self):
        while not self._beep_stop_event.is_set():
            # Beep ON
            self._buzzer_on()
            elapsed = 0.0
            while elapsed < BUZZER_BEEP_DURATION:
                if self._beep_stop_event.is_set():
                    break
                time.sleep(0.1)
                elapsed += 0.1
            self._buzzer_off()

            if self._beep_stop_event.is_set():
                break

            # Silence window - mic listens here
            if self._on_silence_start:
                self._on_silence_start()

            elapsed = 0.0
            while elapsed < BUZZER_BEEP_PAUSE:
                if self._beep_stop_event.is_set():
                    break
                time.sleep(0.1)
                elapsed += 0.1

            if self._on_silence_end:
                self._on_silence_end()

    def _buzzer_on(self):
        if ON_RASPBERRY_PI:
            try:
                GPIO.output(BUZZER_GPIO_PIN, GPIO.HIGH)
            except Exception as e:
                log.error(f"Buzzer ON error: {e}")
        else:
            log.info("[BEEP ON]")

    def _buzzer_off(self):
        if ON_RASPBERRY_PI:
            try:
                GPIO.output(BUZZER_GPIO_PIN, GPIO.LOW)
            except Exception as e:
                log.error(f"Buzzer OFF error: {e}")
        else:
            log.info("[BEEP OFF]")

    def send_sos(self, reason="Fall detected"):
        log.alert(f"SOS triggered: {reason}")
        threading.Thread(
            target=self._send_gsm_sms,
            args=(SOS_MESSAGE,),
            daemon=True
        ).start()

    def send_sos_cancel(self):
        log.info("Sending SOS cancel SMS")
        threading.Thread(
            target=self._send_gsm_sms,
            args=(SOS_CANCEL_MESSAGE,),
            daemon=True
        ).start()

    def _send_gsm_sms(self, message):
        valid_contacts = [
            c for c in EMERGENCY_CONTACTS
            if c and "XXXXXXXXXX" not in c
        ]

        if not valid_contacts:
            log.warning("No valid contacts in config.py - SMS not sent")
            return

        if not ON_RASPBERRY_PI:
            for contact in valid_contacts:
                log.alert(f"[SIMULATED SMS to {contact}]: {message}")
            return

        try:
            gsm = serial.Serial(GSM_SERIAL_PORT, baudrate=GSM_BAUD_RATE, timeout=1)
            time.sleep(1)

            for number in valid_contacts:
                try:
                    gsm.write(b'AT\r')
                    time.sleep(0.5)
                    gsm.write(b'AT+CMGF=1\r')
                    time.sleep(0.5)
                    gsm.write(f'AT+CMGS="{number}"\r'.encode())
                    time.sleep(0.5)
                    gsm.write(f'{message}\x1A'.encode())
                    time.sleep(4)
                    log.info(f"SMS sent to {number}")
                except Exception as e:
                    log.error(f"SMS failed to {number}: {e}")

            gsm.close()

        except serial.SerialException as e:
            log.error(f"GSM module error: {e}")
        except Exception as e:
            log.error(f"SMS error: {e}")

    def cleanup(self):
        self.stop_beep()
        if ON_RASPBERRY_PI:
            try:
                GPIO.cleanup()
            except Exception:
                pass
