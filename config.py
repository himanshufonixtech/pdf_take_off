import os
from dotenv import load_dotenv, dotenv_values

# Store initial environment copy to prioritize pre-set shell environment variables (e.g. in production)
INITIAL_ENV = dict(os.environ)

# Directory settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure necessary directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Dynamic getters to ensure any manual edits to .env are picked up immediately on subsequent calls
def get_openai_api_key():
    reload_config()
    return os.getenv("OPENAI_API_KEY")

def get_openai_api_base_url():
    reload_config()
    return os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")

def get_openai_model():
    reload_config()
    return os.getenv("OPENAI_MODEL", "gpt-4o")

def get_openai_vision_model():
    reload_config()
    return os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

# Module level globals
OPENAI_API_KEY = None
OPENAI_API_BASE_URL = None
OPENAI_MODEL = None
OPENAI_VISION_MODEL = None

def reload_config():
    """Reload environment variables from .env dynamically."""
    global OPENAI_API_KEY, OPENAI_API_BASE_URL, OPENAI_MODEL, OPENAI_VISION_MODEL
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        env_values = dotenv_values(env_path)
        for k, v in env_values.items():
            # Update os.environ with non-placeholder values from .env
            if v and not v.strip().startswith("your-"):
                os.environ[k] = v
                
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

# Run initial load
reload_config()

print("Configuration loaded. Uploads directory:", UPLOADS_DIR)

# Performance tuning for classification
# Number of sample pages to inspect when classifying a PDF (keeps work fast)
CLASSIFY_SAMPLE_PAGES = int(os.getenv("CLASSIFY_SAMPLE_PAGES", "3"))
# Enable parallel classification of files in a single takeoff job
PARALLEL_CLASSIFY = os.getenv("PARALLEL_CLASSIFY", "true").lower() in ("1", "true", "yes")
# Maximum workers used for parallel classification
MAX_CLASSIFY_WORKERS = int(os.getenv("MAX_CLASSIFY_WORKERS", "4"))

# Extraction parallelism tuning
# Enable parallel extraction of files (plans/nathers/basix)
PARALLEL_EXTRACTION = os.getenv("PARALLEL_EXTRACTION", "true").lower() in ("1", "true", "yes")
# Maximum workers used for parallel extraction
MAX_EXTRACTION_WORKERS = int(os.getenv("MAX_EXTRACTION_WORKERS", "4"))
