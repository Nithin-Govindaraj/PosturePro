# ─────────────────────────────────────────────
#  voice_listener.py  —  Vosk keyword detection
#
#  Mic listens ONLY during beep silence windows.
#  This means no beep noise interfering with Vosk.
#  Much better accuracy than always-on listening.
#
#  Requires:
#    pip install vosk sounddevice webrtcvad
#    Model: models/vosk-model-small-en-us-0.15/
# ─────────────────────────────────────────────

import os
import json
import queue
import struct
import threading
from typing import Optional

from config import VAD_AGGRESSIVENESS, VOICE_CONFIDENCE_THRESHOLD
from logger import log

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    log.warning("sounddevice not installed")

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    log.warning("vosk not installed")

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

OK_PHRASES = [
    "okay", "ok",
    "i'm ok", "i am ok", "im ok",
    "i'm okay", "i am okay", "im okay",
    "i ok", "alright", "stop", "fine", "cancel","Good", 
]

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000
BLOCK_SIZE  = 480       # 30ms — required by webrtcvad
NOISE_GATE_RMS = 100    # ignore audio below this RMS


class VoiceListener:
    """
    Listens for 'okay' during beep silence windows only.
    Mic is active ONLY when beep is OFF (silence window).
    This eliminates beep interference with Vosk completely.
    """

    def __init__(self, state_machine):
        self.state_machine = state_machine
        self._thread: Optional[threading.Thread] = None
        self._stop_event    = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()
        self._active        = False   # True = silence window, listen now
        self._available     = SOUNDDEVICE_AVAILABLE and VOSK_AVAILABLE
        self._model         = None
        self._vad           = None

    def start(self):
        if not self._available:
            log.warning("Voice listener unavailable — check vosk + sounddevice")
            return

        if not os.path.isdir(MODEL_PATH):
            log.warning(f"Vosk model not found: {MODEL_PATH}")
            self._available = False
            return

        log.info("Loading Vosk model...")
        try:
            self._model = Model(MODEL_PATH)
        except Exception as e:
            log.error(f"Vosk model load failed: {e}")
            self._available = False
            return

        if WEBRTCVAD_AVAILABLE:
            self._vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
            log.info(f"WebRTC VAD enabled (aggressiveness={VAD_AGGRESSIVENESS})")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="VoiceListener")
        self._thread.start()
        log.info("Voice listener started — listens during beep silence windows")

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=3)
            log.info("Voice listener stopped")

    def set_active(self, active: bool):
        """
        True  = silence window started, mic should listen now
        False = beep resumed or system recovered, stop listening
        """
        self._active = active
        if active:
            log.info("Silence window — MIC ON, say 'okay' to cancel")
        else:
            log.debug("Beep resuming — MIC OFF")

    @property
    def is_available(self) -> bool:
        return self._available

    def _run(self):
        recognizer = KaldiRecognizer(self._model, SAMPLE_RATE)
        recognizer.SetWords(True)

        def _audio_callback(indata, frames, time_info, status):
            self._audio_queue.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
                device=1,
                callback=_audio_callback,
            ):
                log.debug("Microphone stream opened")

                while not self._stop_event.is_set():
                    try:
                        chunk = self._audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    # Only process during silence window
                    if not self._active:
                        continue

                    # Noise gate
                    if not self._passes_noise_gate(chunk):
                        continue

                    # VAD filter
                    if self._vad is not None:
                        try:
                            if not self._vad.is_speech(chunk, SAMPLE_RATE):
                                continue
                        except Exception:
                            pass

                    # Vosk recognition
                    if recognizer.AcceptWaveform(chunk):
                        result = json.loads(recognizer.Result())
                        text   = result.get("text", "").lower().strip()
                        if text:
                            log.debug(f"Voice (final): '{text}'")
                            self._check_ok_with_confidence(result, text)
                    else:
                        partial = json.loads(recognizer.PartialResult())
                        p_text  = partial.get("partial", "").lower().strip()
                        if p_text:
                            log.debug(f"Voice (partial): '{p_text}'")
                            for phrase in OK_PHRASES:
                                if phrase in p_text:
                                    log.info(f"Partial OK match: '{p_text}'")
                                    self.state_machine.voice_cancel_received = True
                                    return

        except Exception as e:
            log.error(f"Voice listener error: {e}")

    def _passes_noise_gate(self, chunk: bytes) -> bool:
        try:
            samples = struct.unpack(f"{len(chunk)//2}h", chunk)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            return rms >= NOISE_GATE_RMS
        except Exception:
            return True

    def _check_ok_with_confidence(self, result: dict, text: str):
        for phrase in OK_PHRASES:
            if phrase not in text:
                continue
            words = result.get("result", [])
            if words:
                phrase_words  = phrase.split()
                confidences   = []
                for pw in phrase_words:
                    for w in words:
                        if w.get("word", "") == pw:
                            confidences.append(w.get("conf", 1.0))
                            break
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    log.debug(f"Confidence for '{phrase}': {avg_conf:.2f}")
                    if avg_conf >= VOICE_CONFIDENCE_THRESHOLD:
                        log.info(f"OK phrase confirmed (conf={avg_conf:.2f}): '{text}'")
                        self.state_machine.voice_cancel_received = True
                        return
                    else:
                        log.debug(f"Low confidence ({avg_conf:.2f}) — ignoring")
                        return
            else:
                log.info(f"OK phrase matched: '{text}'")
                self.state_machine.voice_cancel_received = True
                return