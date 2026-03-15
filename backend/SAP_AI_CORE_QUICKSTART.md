# SAP AI Core Quick Start Guide

## What Changed?

Your Docs-QA application now supports using SAP AI Core API instead of running models locally on your machine.

## Quick Setup (3 Steps)

### 1. Get Your SAP AI Core Credentials

From your SAP BTP service key, copy these values:
- Client ID
- Client Secret  
- API URL
- Auth URL

### 2. Update `.env` File

Replace the placeholder values in `backend/.env`:

```env
# Switch to SAP AI Core
MODEL_PROVIDER=sap_ai_core

# Add your credentials
SAP_AI_CORE_API_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
SAP_AI_CORE_CLIENT_ID=your_actual_client_id_here
SAP_AI_CORE_CLIENT_SECRET=your_actual_client_secret_here
SAP_AI_CORE_AUTH_URL=https://your-tenant.authentication.eu10.hana.ondemand.com/oauth/token

# Optional: Change models (defaults are good)
CHAT_MODEL_NAME=claude-3-5-sonnet-20241022
EMBEDDING_MODEL_NAME=text-embedding-3-large
```

### 3. Restart Your Application

```bash
cd backend
python run.py
```

Look for these messages confirming SAP AI Core is active:
```
SAP AI Core chat model initialized: claude-3-5-sonnet-20241022
SAP AI Core embedding model initialized: text-embedding-3-large
```

## That's It!

Your application now uses SAP AI Core for:
- ✅ **Chat responses** - Claude 3.5 Sonnet (much better than local Qwen!)
- ✅ **Embeddings** - text-embedding-3-large (better quality)
- ✅ **No local models** - Saves memory and startup time

## Switch Back to Local Models

Just change one line in `.env`:

```env
MODEL_PROVIDER=local
```

## Important Notes

### About Claude and Embeddings

⚠️ **Claude does NOT generate embeddings!** 
- Claude is only used for chat/text generation
- For embeddings, you need a separate embedding model (like `text-embedding-3-large`)
- The application handles this automatically

### Model Names Must Match - IMPORTANT!

⚠️ **The model names in `.env` must match your actual SAP AI Core deployment IDs exactly!**

**How to find your deployment IDs:**

1. Log into SAP BTP Cockpit
2. Navigate to your SAP AI Core instance
3. Go to "ML Operations" > "Deployments"
4. Copy the exact **Deployment ID** (not the model name or scenario ID)
5. Use that exact ID in your `.env` file

**Common mistake:** Using model names like `text-embedding-3-large` when your deployment ID might be something like `d12345-embedding` or `text-embedding-ada-002`.

**Example:**
```env
# ❌ WRONG - using generic model name
EMBEDDING_MODEL_NAME=text-embedding-3-large

# ✅ CORRECT - using actual deployment ID from SAP AI Core
EMBEDDING_MODEL_NAME=d7a8b9c0-text-embedding
```

**If you get 404 errors**, it means the deployment ID doesn't exist or is incorrect.

### First Time Setup

If you're switching from local embeddings to SAP AI Core embeddings:
1. Existing embeddings in vector DB won't match
2. You'll need to re-upload documents to generate new embeddings
3. Or switch back to `MODEL_PROVIDER=local` to keep using existing embeddings

## Need Help?

- **Full documentation**: See `SAP_AI_CORE_GUIDE.md`
- **Troubleshooting**: Check the guide for common issues
- **SAP Support**: Contact SAP if API issues occur

## Files Changed

The following files were modified to support SAP AI Core:

1. `backend/app/__init__.py` - Configuration
2. `backend/app/helpers/sap_ai_core_client.py` - API client (NEW)
3. `backend/app/models/chat.py` - Chat model abstraction
4. `backend/app/helpers/embeddings.py` - Embedding abstraction
5. `backend/.env` - Configuration values

All changes are backward compatible - local models still work!
