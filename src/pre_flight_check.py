# pre_flight_check.py - Run this before main.py to verify setup
# Usage: python pre_flight_check.py

import os
import sys

def check(name, condition, fix=""):
    status = "OK  " if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition and fix:
        print(f"         Fix: {fix}")
    return condition

print("\n" + "="*55)
print("  PosturePro - Pre-Flight Check")
print("="*55 + "\n")

all_ok = True

print("[1] Python Packages")
packages = {
    "mediapipe":   "import mediapipe",
    "cv2":         "import cv2",
    "numpy":       "import numpy",
    "vosk":        "import vosk",
    "sounddevice": "import sounddevice",
    "webrtcvad":   "import webrtcvad",
    "serial":      "import serial",
}
for pkg, imp in packages.items():
    try:
        exec(imp)
        check(pkg, True)
    except ImportError:
        all_ok = False
        check(pkg, False, f"pip install {pkg}")

print("\n[2] Project Files")
files = [
    "main.py", "config.py", "fall_logic.py",
    "alert_manager.py", "voice_listener.py",
    "pose_detector.py", "features.py", "logger.py",
]
for f in files:
    exists = os.path.exists(f)
    all_ok = all_ok and exists
    check(f, exists, "File missing from project folder")

print("\n[3] Vosk Speech Model")
model_path = "models/vosk-model-small-en-us-0.15"
exists = os.path.isdir(model_path)
all_ok = all_ok and exists
check(model_path, exists, "Download from https://alphacephei.com/vosk/models")

print("\n[4] Config - Emergency Contacts")
try:
    import config
    contacts = config.EMERGENCY_CONTACTS
    valid = [c for c in contacts if "XXXXXXXXXX" not in c and c]
    contacts_ok = len(valid) >= 1
    all_ok = all_ok and contacts_ok
    check(f"Valid contacts ({len(valid)}/3)", contacts_ok,
          "Set real phone numbers in config.py EMERGENCY_CONTACTS")
except Exception as e:
    all_ok = False
    print(f"  Error reading config.py: {e}")

print("\n" + "="*55)
if all_ok:
    print("  ALL CHECKS PASSED - Ready to run: python main.py")
else:
    print("  SOME CHECKS FAILED - Fix issues above first")
print("="*55 + "\n")

sys.exit(0 if all_ok else 1)
