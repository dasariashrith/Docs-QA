#!/usr/bin/env python3
"""
Helper script to list available SAP AI Core deployments.
Run this to find your actual deployment IDs.

Usage:
    python list_sap_deployments.py
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SAP_AI_CORE_API_URL = os.getenv('SAP_AI_CORE_API_URL')
SAP_AI_CORE_CLIENT_ID = os.getenv('SAP_AI_CORE_CLIENT_ID')
SAP_AI_CORE_CLIENT_SECRET = os.getenv('SAP_AI_CORE_CLIENT_SECRET')
SAP_AI_CORE_AUTH_URL = os.getenv('SAP_AI_CORE_AUTH_URL')
SAP_AI_CORE_RESOURCE_GROUP = os.getenv('SAP_AI_CORE_RESOURCE_GROUP', 'default')


def get_access_token():
    """Get OAuth2 access token."""
    print("🔐 Authenticating with SAP AI Core...")
    
    try:
        response = requests.post(
            SAP_AI_CORE_AUTH_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': SAP_AI_CORE_CLIENT_ID,
                'client_secret': SAP_AI_CORE_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        token = response.json()['access_token']
        print("✅ Authentication successful!\n")
        return token
    except Exception as e:
        print(f"❌ Authentication failed: {e}\n")
        print("Please check your credentials in .env file:")
        print("  - SAP_AI_CORE_CLIENT_ID")
        print("  - SAP_AI_CORE_CLIENT_SECRET")
        print("  - SAP_AI_CORE_AUTH_URL")
        exit(1)


def list_deployments(token):
    """List all deployments in the resource group."""
    print(f"📋 Listing deployments in resource group: {SAP_AI_CORE_RESOURCE_GROUP}\n")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'AI-Resource-Group': SAP_AI_CORE_RESOURCE_GROUP,
        'Content-Type': 'application/json'
    }
    
    try:
        # Try v2 API first
        url = f"{SAP_AI_CORE_API_URL}/v2/lm/deployments"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            # Try v1 API
            url = f"{SAP_AI_CORE_API_URL}/lm/deployments"
            response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        
        deployments = data.get('resources', [])
        
        if not deployments:
            print("⚠️  No deployments found in this resource group.")
            print(f"   Resource group: {SAP_AI_CORE_RESOURCE_GROUP}")
            print("   Check if deployments exist in a different resource group.\n")
            return
        
        print(f"Found {len(deployments)} deployment(s):\n")
        print("=" * 80)
        
        chat_models = []
        embedding_models = []
        other_models = []
        
        for deployment in deployments:
            dep_id = deployment.get('id', 'N/A')
            scenario_id = deployment.get('scenarioId', 'N/A')
            status = deployment.get('status', 'N/A')
            config_id = deployment.get('configurationId', 'N/A')
            details = deployment.get('details', {})
            
            # Get additional details if available
            resources = details.get('resources', {})
            backend_details = details.get('backendDetails', {})
            model_name = backend_details.get('model', {}).get('name', 'Unknown')
            model_version = backend_details.get('model', {}).get('version', '')
            
            deployment_info = (dep_id, scenario_id, status, config_id, model_name, model_version)
            
            # Categorize by scenario or config
            scenario_lower = scenario_id.lower()
            config_lower = config_id.lower()
            
            if scenario_id == 'foundation-models':
                # Foundation models can be chat or embeddings
                if 'embed' in model_name.lower():
                    embedding_models.append(deployment_info)
                else:
                    chat_models.append(deployment_info)
            elif scenario_id == 'orchestration':
                # Orchestration is typically for complex workflows/chat
                chat_models.append(deployment_info)
            elif 'embed' in scenario_lower or 'embed' in config_lower:
                embedding_models.append(deployment_info)
            elif 'chat' in scenario_lower or 'gpt' in scenario_lower or 'claude' in scenario_lower or 'llm' in scenario_lower:
                chat_models.append(deployment_info)
            else:
                other_models.append(deployment_info)
        
        # Print chat models
        if chat_models:
            print("\n🤖 CHAT MODELS (for CHAT_MODEL_NAME):")
            print("-" * 80)
            for dep_id, scenario_id, status, config_id, model_name, model_version in chat_models:
                status_icon = "✅" if status == "RUNNING" else "⚠️ "
                print(f"{status_icon} Deployment ID: {dep_id}")
                print(f"   Scenario: {scenario_id}")
                print(f"   Status: {status}")
                print(f"   Model: {model_name} {model_version}".strip())
                print(f"   Config: {config_id}")
                print()
        
        # Print embedding models
        if embedding_models:
            print("\n📊 EMBEDDING MODELS (for EMBEDDING_MODEL_NAME):")
            print("-" * 80)
            for dep_id, scenario_id, status, config_id, model_name, model_version in embedding_models:
                status_icon = "✅" if status == "RUNNING" else "⚠️ "
                print(f"{status_icon} Deployment ID: {dep_id}")
                print(f"   Scenario: {scenario_id}")
                print(f"   Status: {status}")
                print(f"   Model: {model_name} {model_version}".strip())
                print(f"   Config: {config_id}")
                print()
        
        # Print other models
        if other_models:
            print("\n🔧 OTHER DEPLOYMENTS:")
            print("-" * 80)
            for dep_id, scenario_id, status, config_id, model_name, model_version in other_models:
                status_icon = "✅" if status == "RUNNING" else "⚠️ "
                print(f"{status_icon} Deployment ID: {dep_id}")
                print(f"   Scenario: {scenario_id}")
                print(f"   Status: {status}")
                print(f"   Model: {model_name} {model_version}".strip())
                print(f"   Config: {config_id}")
                print()
        
        print("=" * 80)
        print("\n📝 Next Steps:")
        print("1. Copy the Deployment ID of your desired model")
        print("2. Update your .env file:")
        print("   - CHAT_MODEL_NAME=<your-chat-deployment-id>")
        print("   - EMBEDDING_MODEL_NAME=<your-embedding-deployment-id>")
        print("3. Make sure to use deployments with status 'RUNNING'")
        print("4. Restart your application: python run.py\n")
        
    except Exception as e:
        print(f"❌ Failed to list deployments: {e}\n")
        print("Possible issues:")
        print("  - Check SAP_AI_CORE_API_URL in .env")
        print("  - Verify resource group name")
        print("  - Ensure you have permissions to list deployments\n")


def main():
    """Main function."""
    print("\n" + "=" * 80)
    print("SAP AI Core Deployment Finder")
    print("=" * 80 + "\n")
    
    # Validate configuration
    if not all([SAP_AI_CORE_API_URL, SAP_AI_CORE_CLIENT_ID, 
                SAP_AI_CORE_CLIENT_SECRET, SAP_AI_CORE_AUTH_URL]):
        print("❌ Missing SAP AI Core configuration in .env file!\n")
        print("Please ensure these variables are set:")
        print("  - SAP_AI_CORE_API_URL")
        print("  - SAP_AI_CORE_CLIENT_ID")
        print("  - SAP_AI_CORE_CLIENT_SECRET")
        print("  - SAP_AI_CORE_AUTH_URL")
        print("  - SAP_AI_CORE_RESOURCE_GROUP (optional, default: 'default')\n")
        exit(1)
    
    # Get token and list deployments
    token = get_access_token()
    list_deployments(token)


if __name__ == "__main__":
    main()
