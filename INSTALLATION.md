# Installation Guide
 
## Requirements

- Raspberry Pi 4B with Raspberry Pi OS installed
- Python 3.9
- 32GB microSD card
- Hardware assembled as per README

---

## Steps

### 1. Clone Repository

```bash
git clone https://github.com/Nithin-Govindaraj/Posture-Pro.git
cd Posture-Pro
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Vosk Model Setup

```bash
cd models/
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..
```

Expected path after extraction: `models/vosk-model-small-en-us-0.15/`

### 5. GSM Module UART Setup

Enable UART on Raspberry Pi:

1. Run `sudo raspi-config`
2. Go to **Interface Options → Serial Port**
3. Login shell over serial → **No**
4. Serial port hardware enabled → **Yes**
5. Reboot: `sudo reboot`

### 6. Configure Emergency Contacts

Open `config.py` and replace placeholder numbers:

```python
EMERGENCY_CONTACTS = [
    "+91xxxxxxxxxx",  # Contact 1
    "+91xxxxxxxxxx",  # Contact 2
    "+91xxxxxxxxxx",  # Contact 3
]
```

> ⚠️ At least one valid number is required. Add `config.py` to `.gitignore` — do not commit real phone numbers.

### 7. Camera & Mic Index (if needed)

- Camera not detected → change `CAMERA_INDEX = 0` to `1` in `config.py`
- Mic not detected → change `device=0` to `1` in `voice_listener.py`

### 8. Run

```bash
python main.py
```

Once running, refer to [System Behaviour](README.md#system-behaviour) in the README to understand detection thresholds, alert timing, and how voice cancellation works.

### 9. Autoboot on Power On (Optional)

```bash
bash autoboot_setup.sh
```
