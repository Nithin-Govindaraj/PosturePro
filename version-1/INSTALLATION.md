# Installation Guide — Laptop Version

## Requirements
- Python 3.9
- Windows 10/11

## Setup

### 1. Clone Repository
```bash
git clone https://github.com/NithinGovindaraj/PosturePro.git
cd PosturePro/version-1
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Vosk Model Setup
```bash
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..
```
Or download manually from https://alphacephei.com/vosk/models and extract into `models/` folder.

### 5. Add Emergency Contacts
Open `config.py` and replace `+91XXXXXXXXXX` with real numbers:
```python
EMERGENCY_CONTACTS = [
    "+919876543210",
    "+919123456789",
    "+919988776655",
]
```

### 6. Camera Setup
Default camera index is `1` in `config.py`.
If webcam not detected change to `0`:
```python
CAMERA_INDEX = 0
```

### 7. Microphone Setup
Default mic device is `0` in `voice_listener.py`.
If mic not detected change to `1`:
```python
device=1,
```

### 8. Run
```bash
python main.py
```
Press **Q** to quit.

---

## Notes
- SMS alerts are printed to terminal in this version
- No GSM module or internet required
- System speaker used for beep alert
