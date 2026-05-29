# PosturePro: Vision-Based Fall Detection System
### Version 1.0 — Laptop/PC Version

Real-time fall detection using MediaPipe Pose estimation, Kalman filtering, and offline voice recognition. This version runs on a standard laptop or PC with a webcam and microphone.

> **Note:** SMS alerts are simulated in the terminal in this version. For real GSM-based SMS alerts on Raspberry Pi, see [Version 2.0](https://github.com/NithinGovindaraj/PosturePro-Vision-Based-Fall-Detection-System)

---

## Problem Statement

Falls are a leading cause of injury-related mortality among elderly individuals. Existing wearable-based solutions suffer from low user compliance. Cloud-dependent camera systems require constant internet connectivity, unavailable in many areas.

## How We Differ

PosturePro is a fully offline, rule-based system requiring no wearables and no internet. It uses lightweight pose estimation with Kalman filtering and multi-signal voting for robust fall classification.

---

## Features

- MediaPipe Pose estimation (33 3D landmarks)
- Kalman filter for keypoint smoothing
- Multi-signal voting classifier (torso angle, hip position, SAR, hip joint angle)
- Periodic beep-silence alert (2s ON / 5s OFF) with voice cancellation window
- Offline Vosk speech recognition for alert cancellation
- SMS alert simulated in terminal (no internet needed)
- No wearables required

---

## System Timings

| Event | Timing |
|-------|--------|
| Fall confirmation | 7 seconds motionless |
| Beep ON | 2 seconds |
| Beep OFF (mic listens) | 5 seconds |
| SOS trigger | 30 seconds no response |

---

## Voice Cancellation

Say any of these during the 5 second silence window:
**okay, ok, i'm ok, alright, stop, fine, cancel**

---

## Hardware Required

| Component | Specs |
|-----------|-------|
| Laptop/PC | Windows 10/11 |
| Webcam | Built-in or USB |
| Microphone | Built-in or USB |

---

## Tech Stack

### Software
- Python 3.9
- MediaPipe 0.10.14
- OpenCV 4.8.0
- NumPy >= 1.23.0
- Vosk 0.3.45
- SoundDevice 0.4.6
- WebRTCVAD 2.0.10

---

## System Flow

```
Person falls → 7 second confirmation → Beep starts (2s ON / 5s OFF)
    ↓
During silence: Say "okay" → Beep stops
    ↓
OR: No response 30s → SMS simulated in terminal
    ↓
Movement OR voice cancel → Cancel SMS in terminal
```

## Project Structure

```
PosturePro/
├── main.py
├── config.py
├── pose_detector.py
├── fall_logic.py
├── alert_manager.py
├── voice_listener.py
├── features.py
├── logger.py
├── requirements.txt
├── INSTALLATION.md
└── models/
```

---

## Emergency Contacts Setup

Open `config.py` and replace `+91XXXXXXXXXX` with real numbers:
```python
EMERGENCY_CONTACTS = [
    "+919876543210",
    "+919123456789",
    "+919988776655",
]
```
In this version SMS will be printed to terminal showing which number would receive the alert.

---

## Test Runs

System tested under varied lighting conditions and body orientations on laptop.

---

## References

[1] C. Lugaresi et al., "MediaPipe: A Framework for Building Perception Pipelines," arXiv, 2019.
[2] W. Min et al., "Human Fall Detection Using Normalized Shape Aspect Ratio," Multimedia Tools and Applications, 2018.
[3] R.E. Kalman, "A New Approach to Linear Filtering and Prediction Problems," J. Basic Engineering, 1960.
[4] V. Bevilacqua et al., "Fall Detection Using Ensemble Learning with Sliding Window Voting," Applied Sciences, 2021.
[5] Alpha Cephei, "Vosk Offline Speech Recognition Toolkit," https://alphacephei.com/vosk, 2021.

---

## Author

**Nithin G**
Department of Electronics and Communication Engineering
SNS College of Technology, Coimbatore

---

**Status:** Complete — Laptop Version
**Version 2.0 (Raspberry Pi):** [PosturePro v2](https://github.com/NithinGovindaraj/PosturePro-Vision-Based-Fall-Detection-System)
