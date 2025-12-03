

# --- System Configuration ---

# The number of seconds of inactivity before the timer pauses.
GRACE_PERIOD_SECONDS = 15

# How often to check for screen motion (in seconds).
# A higher value saves CPU, a lower value is more responsive.
SCREEN_MOTION_CHECK_INTERVAL_SECONDS = 2.0

# --- Application Keywords ---
# These are case-insensitive keywords found in window titles.

PRODUCTIVE_KEYWORDS = [
    # Development
    'visual studio code', 'pycharm', 'idea', 'android studio', 'sublime text',
    'terminal', 'command prompt', 'powershell', 'git',
    
    # Office & Writing
    'word', 'excel', 'powerpoint', 'onenote',
    'google docs', 'google sheets', 'google slides',
    
    # Communication
    'zoom', 'microsoft teams', 'slack',
    
    # Design & Creativity
    'photoshop', 'illustrator', 'figma', 'canva', 'autocad',
    
    # Research & Learning
    'github', 'stackoverflow', 'jira', 'trello', 'documentation'
]

UNPRODUCTIVE_KEYWORDS = [
    # Social Media
    'instagram', 'twitter', 'facebook', 'reddit', 'pinterest', 'tiktok', 'Producitvity Monitor'
    
    # Entertainment & Streaming
    'youtube', 'netflix', 'prime video', 'disney+', 'hulu',
    
    # Music & Audio
    'spotify', 'apple music', 'soundcloud',
    
    # Gaming & Chat
    'steam', 'epic games', 'discord', 'telegram'
]
