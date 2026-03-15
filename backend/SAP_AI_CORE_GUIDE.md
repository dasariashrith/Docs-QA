# SAP AI Core Integration Guide

This guide explains how to configure and use SAP AI Core API with your Docs-QA application instead of running models locally.

## Overview

Your application now supports two model providers:

1. **Local Models** (default): Uses Hugging Face models running on your machine
2. **SAP AI Core**: Uses SAP AI Core API for both chat and embeddings

## Benefits of Using SAP AI Core

- **No local model loading**: Saves memory and reduces startup time
- **Better quality**: Claude 3.5 Sonnet provides significantly better responses than local Qwen 0.5B
- **Scalability**: API-based models handle multiple requests efficiently
- **No GPU required**: All processing happens in the cloud
- **Flexible model selection**: Easily switch between different models via environment variables

## Prerequisites

Before configuring SAP AI Core, ensure you have:

1. An active SAP BTP account with SAP AI Core enabled
2. SAP AI Core service instance created
3. Service key generated for your SAP AI Core instance
4. Model deployments configured in SAP AI Core for:
   - Chat model (e.g., Claude 3.5 Sonnet, GPT-4)
   - Embedding model (e.g., text-embedding-3-large)

## Configuration Steps

### Step 1: Get SAP AI Core Credentials

1. Log into your SAP BTP cockpit
2. Navigate to your SAP AI Core service instance
3. Create or view an existing service key
4. Copy the following values from your service key:
   - `clientid` (Client ID)
   - `clientsecret` (Client Secret)
   - `url` (API URL)
   - `serviceurls.AI_API_URL` (AI API URL, if different from `url`)
   - OAuth2 token endpoint URL

### Step 2: Update .env File

Open `backend/.env` and update the SAP AI Core configuration:

```env
# Change from 'local' to 'sap_ai_core'
MODEL_PROVIDER=sap_ai_core

# SAP AI Core Configuration
SAP_AI_CORE_API_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
SAP_AI_CORE_CLIENT_ID=your_actual_client_id
SAP_AI_CORE_CLIENT_SECRET=your_actual_client_secret
SAP_AI_CORE_AUTH_URL=https://your-tenant.authentication.eu10.hana.ondemand.com/oauth/token
SAP_AI_CORE_RESOURCE_GROUP=default

# Model Configuration
CHAT_MODEL_NAME=claude-3-5-sonnet-20241022
EMBEDDING_MODEL_NAME=text-embedding-3-large
```

### Step 3: Verify Model Deployments

Ensure your SAP AI Core instance has the following model deployments:

1. **Chat Model**: 
   - Recommended: `claude-3-5-sonnet-20241022`
   - Alternatives: `gpt-4`, `gpt-4-turbo`, `claude-3-opus`
   
2. **Embedding Model**:
   - Recommended: `text-embedding-3-large`
   - Alternatives: `text-embedding-3-small`, `text-embedding-ada-002`

**Note**: The model names in `.env` should match your deployment IDs in SAP AI Core.

### Step 4: Test the Configuration

1. Restart your application:
   ```bash
   cd backend
   python run.py
   ```

2. Check the console output for successful initialization:
   ```
   SAP AI Core chat model initialized: claude-3-5-sonnet-20241022
   SAP AI Core embedding model initialized: text-embedding-3-large
   ```

3. Test with a chat query to verify it's working correctly.

## Understanding the Configuration

### MODEL_PROVIDER

Controls which model provider to use:
- `local`: Uses local Hugging Face models (default)
- `sap_ai_core`: Uses SAP AI Core API

### SAP_AI_CORE_API_URL

The base URL for your SAP AI Core API endpoint. This typically looks like:
```
https://api.ai.prod.{region}.aws.ml.hana.ondemand.com
```

Replace `{region}` with your region (e.g., `eu-central-1`, `us-east-1`).

### SAP_AI_CORE_CLIENT_ID & SAP_AI_CORE_CLIENT_SECRET

OAuth2 credentials from your SAP AI Core service key. These are used to authenticate API requests.

### SAP_AI_CORE_AUTH_URL

The OAuth2 token endpoint for authentication. Format:
```
https://{tenant}.authentication.{region}.hana.ondemand.com/oauth/token
```

### SAP_AI_CORE_RESOURCE_GROUP

The resource group in SAP AI Core where your models are deployed. Default is `default`.

### CHAT_MODEL_NAME

The deployment ID or name of your chat model in SAP AI Core. Examples:
- `claude-3-5-sonnet-20241022` (Recommended)
- `gpt-4`
- `gpt-4-turbo`
- `claude-3-opus`

### EMBEDDING_MODEL_NAME

The deployment ID or name of your embedding model in SAP AI Core. Examples:
- `text-embedding-3-large` (Recommended)
- `text-embedding-3-small`
- `text-embedding-ada-002`

## Switching Between Local and SAP AI Core

You can easily switch between local and SAP AI Core models:

### Switch to SAP AI Core:
```env
MODEL_PROVIDER=sap_ai_core
```

### Switch back to Local:
```env
MODEL_PROVIDER=local
```

No code changes are required - just update the `.env` file and restart the application.

## Architecture Overview

### Chat Model Flow

1. User sends a message
2. Application checks `MODEL_PROVIDER` setting
3. If `sap_ai_core`:
   - Authenticates with OAuth2
   - Sends request to SAP AI Core API
   - Returns response from Claude/GPT
4. If `local`:
   - Loads local Hugging Face model
   - Generates response locally

### Embedding Model Flow

1. Document chunks need embeddings
2. Application checks `MODEL_PROVIDER` setting
3. If `sap_ai_core`:
   - Authenticates with OAuth2
   - Sends texts to SAP AI Core embedding API
   - Returns embedding vectors
4. If `local`:
   - Uses local `thenlper/gte-large` model
   - Generates embeddings locally

## API Details

### Authentication

The application automatically handles OAuth2 authentication:
- Obtains access token using client credentials
- Caches token with 5-minute buffer before expiry
- Automatically refreshes expired tokens

### Chat Completion API

**Endpoint**: `{SAP_AI_CORE_API_URL}/v2/inference/deployments/{model}/chat/completions`

**Request Format** (OpenAI-compatible):
```json
{
  "messages": [
    {"role": "user", "content": "Your question here"}
  ],
  "max_tokens": 1024,
  "temperature": 0.7
}
```

**Response Format**:
```json
{
  "choices": [
    {
      "message": {
        "content": "AI response here"
      }
    }
  ]
}
```

### Embeddings API

**Endpoint**: `{SAP_AI_CORE_API_URL}/v2/inference/deployments/{model}/embeddings`

**Request Format** (OpenAI-compatible):
```json
{
  "input": ["text 1", "text 2", "text 3"]
}
```

**Response Format**:
```json
{
  "data": [
    {"index": 0, "embedding": [0.1, 0.2, ...]},
    {"index": 1, "embedding": [0.3, 0.4, ...]},
    {"index": 2, "embedding": [0.5, 0.6, ...]}
  ]
}
```

## Troubleshooting

### Authentication Errors

**Error**: "Failed to obtain access token from SAP AI Core"

**Solutions**:
1. Verify `SAP_AI_CORE_CLIENT_ID` and `SAP_AI_CORE_CLIENT_SECRET` are correct
2. Check `SAP_AI_CORE_AUTH_URL` matches your service key
3. Ensure service key hasn't expired
4. Verify network connectivity to SAP BTP

### Model Not Found Errors

**Error**: "SAP AI Core chat completion failed: 404"

**Solutions**:
1. Verify model deployment exists in SAP AI Core
2. Check `CHAT_MODEL_NAME` matches your deployment ID exactly
3. Ensure deployment is in the correct resource group
4. Verify deployment status is "RUNNING"

### Embedding Dimension Mismatch

**Error**: "Vector dimension mismatch"

**Solutions**:
1. If switching from local to SAP AI Core embeddings, you may need to:
   - Delete existing vector database collections
   - Re-upload documents to generate new embeddings
2. Ensure `EMBEDDING_MODEL_NAME` points to a compatible model
3. Check embedding dimensions match your vector DB configuration

### Timeout Errors

**Error**: "Request timeout"

**Solutions**:
1. Check network connectivity
2. Verify SAP AI Core service is available
3. Consider increasing timeout in `sap_ai_core_client.py`
4. Check if model deployment is scaled properly

### Rate Limiting

If you encounter rate limiting errors:
1. Implement retry logic with exponential backoff
2. Batch requests when possible
3. Contact SAP support to increase quotas
4. Consider switching to a higher service tier

## Cost Considerations

When using SAP AI Core:

1. **API Costs**: You're charged per API call and token usage
2. **Model Costs**: Different models have different pricing (Claude > GPT-4 > GPT-3.5)
3. **Embedding Costs**: Charged per 1000 tokens embedded
4. **Deployment Costs**: Ongoing costs for keeping deployments running

**Recommendations**:
- Start with `text-embedding-3-small` instead of `large` to reduce costs
- Use `gpt-3.5-turbo` if Claude is too expensive
- Monitor usage through SAP BTP cockpit
- Set up budget alerts

## Security Best Practices

1. **Never commit credentials**: Keep `.env` file out of version control
2. **Use service keys**: Create dedicated service keys for each environment
3. **Rotate credentials**: Regularly rotate client secrets
4. **Limit permissions**: Use least-privilege principle for service keys
5. **Monitor access**: Review API logs regularly
6. **Use HTTPS**: Ensure all API calls use HTTPS (default)

## Performance Optimization

1. **Batch embeddings**: Generate embeddings in batches for better throughput
2. **Cache responses**: Consider caching frequent queries (not implemented)
3. **Optimize prompts**: Shorter prompts = lower costs and faster responses
4. **Parallel requests**: API can handle multiple concurrent requests
5. **Connection pooling**: Reuse HTTP connections (implemented via `requests` library)

## Support

For issues related to:

- **Application code**: Check project repository issues
- **SAP AI Core**: Contact SAP support or check SAP community forums
- **Model behavior**: Refer to model provider documentation (Anthropic for Claude, OpenAI for GPT)

## Additional Resources

- [SAP AI Core Documentation](https://help.sap.com/docs/ai-core)
- [SAP BTP Cockpit](https://account.hana.ondemand.com/)
- [Claude API Documentation](https://docs.anthropic.com/claude/reference)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
