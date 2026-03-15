"""
SAP AI Core API client for authentication and API calls.
Handles OAuth2 authentication and API requests to SAP AI Core.
"""

import requests
import time
from typing import Dict, List, Optional
from app import (
    SAP_AI_CORE_API_URL,
    SAP_AI_CORE_CLIENT_ID,
    SAP_AI_CORE_CLIENT_SECRET,
    SAP_AI_CORE_AUTH_URL,
    SAP_AI_CORE_RESOURCE_GROUP
)


class SAPAICoreClient:
    """
    Client for SAP AI Core API with OAuth2 authentication.
    Handles token management and API requests.
    """

    def __init__(self):
        self.api_url = SAP_AI_CORE_API_URL
        self.client_id = SAP_AI_CORE_CLIENT_ID
        self.client_secret = SAP_AI_CORE_CLIENT_SECRET
        self.auth_url = SAP_AI_CORE_AUTH_URL
        self.resource_group = SAP_AI_CORE_RESOURCE_GROUP
        
        self.access_token = None
        self.token_expiry = 0
        
        # Validate configuration
        if not all([self.api_url, self.client_id, self.client_secret, self.auth_url]):
            raise ValueError(
                "SAP AI Core configuration is incomplete. "
                "Please set SAP_AI_CORE_API_URL, SAP_AI_CORE_CLIENT_ID, "
                "SAP_AI_CORE_CLIENT_SECRET, and SAP_AI_CORE_AUTH_URL in .env file."
            )

    def _get_access_token(self) -> str:
        """
        Get OAuth2 access token from SAP AI Core.
        Uses client credentials flow.
        """
        # Check if token is still valid (with 5 min buffer)
        if self.access_token and time.time() < (self.token_expiry - 300):
            return self.access_token

        # Request new token
        try:
            response = requests.post(
                self.auth_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            # Set expiry time (default to 3600 seconds if not provided)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to obtain access token from SAP AI Core: {str(e)}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        token = self._get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'AI-Resource-Group': self.resource_group,
            'Content-Type': 'application/json'
        }

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """
        Call SAP AI Core chat completion API.
        
        Args:
            model: Model deployment ID (for foundation-models/orchestration scenarios)
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            str: Generated response text
        """
        # For SAP AI Core Generative AI Hub (foundation-models/orchestration),
        # use the standard chat/completions endpoint WITH model specified in body
        try:
            url = f"{self.api_url}/v2/inference/deployments/{model}/chat/completions"
            
            # Generative AI Hub format: specify model in the request body
            payload = {
                "model": "anthropic--claude-3-5-sonnet",  # Model identifier
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract response from OpenAI-compatible format
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            elif 'completion' in result:
                return result['completion']
            elif 'text' in result:
                return result['text']
                
        except requests.exceptions.RequestException as e:
            print(f"Generative AI Hub format failed: {e}")
            # Try to get more details from the response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Error details: {error_detail}")
                except:
                    print(f"Response text: {e.response.text[:200]}")
        
        # Try without model in body (direct deployment format)
        try:
            url = f"{self.api_url}/v2/inference/deployments/{model}/chat/completions"
            
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
                
        except requests.exceptions.RequestException as e:
            print(f"Direct deployment format failed: {e}")
        
        # All formats failed
        error_msg = (
            f"SAP AI Core chat completion failed for deployment '{model}'.\n\n"
            f"Tried formats:\n"
            f"1. Generative AI Hub format (with model in body)\n"
            f"2. Direct deployment format (without model in body)\n\n"
            f"Recommendations:\n"
            f"- Check if Cline is using a different model identifier\n"
            f"- Verify deployment '{model}' supports Claude\n"
            f"- Or switch to local models: MODEL_PROVIDER=local in .env"
        )
        raise RuntimeError(error_msg)

    def create_embeddings(
        self,
        model: str,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings using SAP AI Core.
        
        Args:
            model: Embedding model deployment ID or name
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        # For foundation-models and orchestration, use different format
        # These are special SAP AI Core scenarios that act as proxies
        
        # Try foundation-models format first (most common for generative AI hub)
        try:
            url = f"{self.api_url}/v2/inference/deployments/{model}/chat/completions"
            
            # Foundation models use a different payload format
            # They expect model specification in the request
            payload = {
                "model": "text-embedding-ada-002",  # Default embedding model
                "input": texts
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract embeddings from OpenAI-compatible format
            if 'data' in result:
                sorted_data = sorted(result['data'], key=lambda x: x['index'])
                return [item['embedding'] for item in sorted_data]
            elif 'embeddings' in result:
                # Alternative format
                return result['embeddings']
                
        except requests.exceptions.RequestException as e:
            print(f"Foundation-models format failed: {e}")
        
        # Try standard embedding endpoint formats
        endpoints_to_try = [
            (f"{self.api_url}/v2/inference/deployments/{model}/embeddings", {"input": texts}),
            (f"{self.api_url}/inference/deployments/{model}/embeddings", {"input": texts}),
        ]
        
        last_error = None
        
        for url, payload in endpoints_to_try:
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                
                if 'data' in result:
                    sorted_data = sorted(result['data'], key=lambda x: x['index'])
                    return [item['embedding'] for item in sorted_data]
                elif 'embeddings' in result:
                    return result['embeddings']
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                continue
        
        # All endpoints failed - provide helpful error message
        error_msg = (
            f"SAP AI Core embedding generation failed for deployment '{model}'.\n\n"
            f"This usually means:\n"
            f"1. The deployment doesn't support embeddings\n"
            f"2. You need a different deployment for embeddings\n"
            f"3. The API format is different than expected\n\n"
            f"Recommendations:\n"
            f"- Run 'python list_sap_deployments.py' to see available deployments\n"
            f"- Look for a deployment with 'embed' in the name\n"
            f"- Or switch to local embeddings: MODEL_PROVIDER=local in .env\n\n"
            f"Last error: {str(last_error)}"
        )
        raise RuntimeError(error_msg)


# Global client instance
_client = None


def get_sap_ai_core_client() -> SAPAICoreClient:
    """Get or create global SAP AI Core client instance."""
    global _client
    if _client is None:
        _client = SAPAICoreClient()
    return _client
