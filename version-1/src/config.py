# config.py - Settings for PosturePro (Laptop Version)

# Camera
CAMERA_INDEX        = 0       # Change to 1 if external webcam not detected
FRAME_WIDTH         = 640
FRAME_HEIGHT        = 480
FPS_TARGET          = 20

# MediaPipe
MP_MODEL_COMPLEXITY          = 0
MP_MIN_DETECTION_CONFIDENCE  = 0.3
MP_MIN_TRACKING_CONFIDENCE   = 0.3

# Keypoint visibility
KEYPOINT_VISIBILITY_THRESHOLD = 0.2

# Kalman Filter
KALMAN_PROCESS_NOISE     = 1e-3
KALMAN_MEASUREMENT_NOISE = 1e-1

# Shape Aspect Ratio
SAR_FALL_THRESHOLD = 0.8

# Joint Angle Thresholds
HIP_ANGLE_FALL_THRESHOLD  = 160.0
KNEE_ANGLE_FALL_THRESHOLD = 160.0

# Velocity
VELOCITY_FALL_THRESHOLD = 8.0

# Voting Window
VOTE_WINDOW_SIZE = 6
VOTE_THRESHOLD   = 3

# Torso angle
TORSO_ANGLE_THRESHOLD = 40.0

# Fall confirmation and SOS timers
FALL_CONFIRM_SECONDS = 7
SOS_TIMER_SECONDS    = 30

# Standing detection
STANDING_NK_BUFFER_PX = 120

# Voice cancellation
VOICE_CANCEL_WINDOW        = 30
VAD_AGGRESSIVENESS         = 1
VOICE_CONFIDENCE_THRESHOLD = 0.3

# Motion detection
MOTION_PIXEL_THRESHOLD = 20

# Buzzer (GPIO on Pi, system speaker on laptop)
BUZZER_GPIO_PIN      = 17
BUZZER_BEEP_DURATION = 2.0
BUZZER_BEEP_PAUSE    = 5.0

# Emergency contacts (SMS simulated on laptop - printed to terminal)
EMERGENCY_CONTACTS = [
    "+91XXXXXXXXXX",
    "+91XXXXXXXXXX",
    "+91XXXXXXXXXX",
]

SOS_MESSAGE        = "FALL ALERT: Person has fallen and is unresponsive. Please check immediately."
SOS_CANCEL_MESSAGE = "FALL ALERT CANCELLED: Person is now responsive. No action needed."

# Logging
LOG_LEVEL            = "INFO"
SHOW_KEYPOINT_VALUES = False
