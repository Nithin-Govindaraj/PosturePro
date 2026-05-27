# PosturePro

### Real-Time Fall Detection with Offline Voice Alert — Edge Deployed

## Overview

Falls are a leading cause of injury-related mortality among elderly, yet existing wearable sensors suffer from poor user compliance and cloud-based vision systems demand constant internet — making them impractical in rural and resource-limited environments.

PosturePro is a fully offline, camera-based fall detection system running entirely on Raspberry Pi 4B. It detects falls using MediaPipe pose estimation with Kalman filtering and multi-signal voting, triggers a local buzzer alert cancellable by voice command, and instantly notifies emergency contacts via GSM SMS — no wearables, no internet, no cloud, just plug and protect.

## Objectives:

- Fall Detection
- Audio Alert
- Voice Cancellation
- SMS Alert
- Edge Deployment

## Features

-  **Pose Estimation** — MediaPipe with 33 body landmarks
-  **Keypoint Smoothing** — Kalman filter for stable tracking
-  **Fall Classifier** — Multi-signal voting (torso angle, hip position, SAR, hip joint angle)
-  **Smart Alert** — Periodic beep-silence pattern (2s ON / 5s OFF)
-  **Voice Cancellation** — Offline Vosk speech recognition to cancel false alarms
-  **SMS Alert** — GSM SIM800L notifies 3 emergency contacts instantly
-  **Fully Offline** — No internet, no cloud, edge deployed on Raspberry Pi

---

## System Behaviour

### Fall Detection

- Fall confirmed after **7 seconds** of continuous fall pose
- 4 signals checked per frame: torso angle, hip position, SAR, hip joint angle
- 3 out of 6 frames must vote fall to confirm

### Alert Pattern

- Buzzer beeps for **2 seconds ON**
- Buzzer silent for **5 seconds OFF** (mic listens here)
- Pattern repeats until cancelled or SOS sent

### Voice Cancellation

- Mic turns ON only during the 5 second silence window
- Say any of these to cancel: **okay, ok, i'm ok, alright, stop, fine, cancel**
- After voice cancel: 60 second cooldown before detection resumes

### SOS Alert

- If no response for **30 seconds** → SMS sent to all 3 contacts
- After SOS: say cancel word OR stand up → cancel SMS sent automatically

---

## System Requirements

<table width="100%">
<tr>
<th width="50%" align="left"> Hardware</th>
<th width="50%" align="left"> Software & Dependencies</th>
</tr>
<tr>
<td valign="top">

* *Raspberry Pi 4B* (2GB+ RAM)
* *MicroSD Card* (32GB) & Reader
* *USB Webcam* & *USB Microphone*
* *Active Piezoelectric Buzzer* (3.3V)
* *SIM000L GSM Module* & Any 2G SIM
* *10µF 25V Capacitor*
* *Resistors:* 1kΩ × 1, 2kΩ × 1
* *Power:* 5V-5A Adapter

</td>
<td valign="top">

* *Python* 3.9
* *MediaPipe* 0.10.14
* *OpenCV* 4.8.0
* *NumPy* 1.24.3
* *Vosk* 0.3.45
* *SoundDevice* 0.4.6
* *WebRTCVAD* 2.0.10
* *PySerial* 3.5
* *RPi.GPIO* 0.7.0

</td>
</tr>
</table>

---

## Test Runs

<img width="588" height="437" alt="Screenshot 2026-05-13 215636" src="https://github.com/user-attachments/assets/406a014c-ca24-4f71-92d2-4a6ed5a823ce" />

<img width="586" height="439" alt="Screenshot 2026-05-13 215815" src="https://github.com/user-attachments/assets/de84b9dc-98e9-4267-aa2c-6eec97ec32ac" />

<img width="589" height="439" alt="Screenshot 2026-05-13 215924" src="https://github.com/user-attachments/assets/9479d10f-6933-41a7-ac6a-3715a0c701f8" />

<img width="591" height="441" alt="Screenshot 2026-05-13 220002" src="https://github.com/user-attachments/assets/cdac5fb1-520c-4fd0-aaf2-e6141f1e9032" />


---

## Getting Started

See [INSTALLATION.md](INSTALLATION.md) to set up and run the project.

---

## References

[1] Lugaresi et al. — MediaPipe: A Framework for Building Perception Pipelines
[DOI](https://doi.org/10.48550/arXiv.1906.08172)

[2] Min et al. — Human Fall Detection Using Normalized Shape Aspect Ratio
[DOI](https://doi.org/10.1007/s11042-018-6794-7)

[3] Kalman — A New Approach to Linear Filtering and Prediction Problems
[DOI](https://doi.org/10.1115/1.3662552)
