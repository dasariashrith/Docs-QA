import os
from dotenv import load_dotenv

load_dotenv()

# Model Provider Configuration
# Options: 'local' or 'sap_ai_core'
MODEL_PROVIDER = os.getenv('MODEL_PROVIDER', 'local')

# SAP AI Core Configuration (required when MODEL_PROVIDER=sap_ai_core)
SAP_AI_CORE_API_URL = os.getenv('SAP_AI_CORE_API_URL', '')
SAP_AI_CORE_CLIENT_ID = os.getenv('SAP_AI_CORE_CLIENT_ID', '')
SAP_AI_CORE_CLIENT_SECRET = os.getenv('SAP_AI_CORE_CLIENT_SECRET', '')
SAP_AI_CORE_AUTH_URL = os.getenv('SAP_AI_CORE_AUTH_URL', '')
SAP_AI_CORE_RESOURCE_GROUP = os.getenv('SAP_AI_CORE_RESOURCE_GROUP', 'default')

# Model Configuration
# For local: Hugging Face model names
# For SAP AI Core: Deployment IDs or model names
CHAT_MODEL_NAME = os.getenv('CHAT_MODEL_NAME', 'claude-3-5-sonnet-20241022')
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-large')

# Legacy configuration (for backward compatibility with local models)
EMBEDDING_MODEL = "thenlper/gte-large"
EMBEDDING_DIMENSION = 1024
SIMILARITY_THRESHOLD = 0.9
CHAT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
CHAT_MODEL_CONTEXT_LENGTH = 262144
