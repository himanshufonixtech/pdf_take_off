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
    return OPENAI_MODEL

def get_openai_vision_model():
    reload_config()
    return OPENAI_VISION_MODEL

# Module level globals
OPENAI_API_KEY = None
OPENAI_API_BASE_URL = None
OPENAI_MODEL = None
OPENAI_VISION_MODEL = None

_AVAILABLE_MODELS_CACHE = None

def _get_active_ollama_models(api_base: str, api_key: str) -> list:
    """Helper to query available models from Ollama to avoid retired model crashes."""
    global _AVAILABLE_MODELS_CACHE
    if _AVAILABLE_MODELS_CACHE is not None:
        return _AVAILABLE_MODELS_CACHE
    
    # Only check if it is Ollama endpoint
    if "ollama.com" not in api_base.lower():
        return []
        
    import urllib.request
    import json
    url = api_base.rstrip('/') + "/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            models = [m["id"] for m in data.get("data", [])]
            _AVAILABLE_MODELS_CACHE = models
            return models
    except Exception as e:
        print(f"[Config] Warn: Failed to fetch active models from Ollama: {e}")
        return []

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
    raw_model = os.getenv("OPENAI_MODEL", "gpt-4o")
    raw_vision_model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

    # Self-healing logic for Ollama model changes
    if "ollama.com" in OPENAI_API_BASE_URL.lower():
        active_models = _get_active_ollama_models(OPENAI_API_BASE_URL, OPENAI_API_KEY)
        if active_models:
            # If current model is not in the active list, heal it!
            if raw_model not in active_models:
                print(f"[Config] Model '{raw_model}' is retired/unavailable on Ollama.")
                # Find best fallback candidate in list
                fallbacks = ["deepseek-v4-flash", "deepseek-v4-pro", "qwen3.5:397b", "gemma4:31b"]
                selected = None
                for fb in fallbacks:
                    if fb in active_models:
                        selected = fb
                        break
                if not selected:
                    selected = active_models[0]
                print(f"[Config] Dynamically healed OPENAI_MODEL to active: '{selected}'")
                raw_model = selected

            if raw_vision_model not in active_models:
                raw_vision_model = raw_model

    OPENAI_MODEL = raw_model
    OPENAI_VISION_MODEL = raw_vision_model

# Run initial load
reload_config()

print("Configuration loaded. Uploads directory:", UPLOADS_DIR)

# Performance tuning for classification
# Number of sample pages to inspect when classifying a PDF (keeps work fast)
CLASSIFY_SAMPLE_PAGES = int(os.getenv("CLASSIFY_SAMPLE_PAGES", "3"))
# Enable parallel classification of files in a single takeoff job
PARALLEL_CLASSIFY = os.getenv("PARALLEL_CLASSIFY", "false").lower() in ("1", "true", "yes")
# Maximum workers used for parallel classification
MAX_CLASSIFY_WORKERS = int(os.getenv("MAX_CLASSIFY_WORKERS", "4"))

# Extraction parallelism tuning
# Enable parallel extraction of files (plans/nathers/basix)
PARALLEL_EXTRACTION = os.getenv("PARALLEL_EXTRACTION", "false").lower() in ("1", "true", "yes")
# Maximum workers used for parallel extraction
MAX_EXTRACTION_WORKERS = int(os.getenv("MAX_EXTRACTION_WORKERS", "4"))
