# System Features & Timings

## Fall Detection
- Fall confirmed after **7 seconds** of continuous fall pose
- 4 signals checked per frame: torso angle, hip position, SAR, hip joint angle
- 3 out of 6 frames must vote fall to confirm

## Alert Pattern
- Beep ON: **2 seconds** (system speaker)
- Beep OFF: **5 seconds** (mic listens here)
- Pattern repeats until cancelled or SOS triggered

## Voice Cancellation
- Mic turns ON only during 5 second silence window
- Say any of these to cancel: **okay, ok, i'm ok, alright, stop, fine, cancel**
- Mic turns OFF when beep resumes
- After voice cancel: 60 second cooldown before fall detection resumes

## SOS Alert
- No response for **30 seconds** → SMS printed to terminal
- After SOS: say cancel word OR stand up → cancel SMS printed

## Emergency Contacts
Open `config.py` and replace `+91XXXXXXXXXX`:
```python
EMERGENCY_CONTACTS = [
    "+919876543210",
    "+919123456789",
    "+919988776655",
]
```

## Camera & Mic
- Camera: `CAMERA_INDEX = 1` in config.py (change to 0 if not working)
- Mic: `device=0` in voice_listener.py (change to 1 if not working)
