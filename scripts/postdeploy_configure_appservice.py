"""
Post-deploy script for Azure App Service deployment.
Updates App Service with agent environment variables after deployment.
"""
import os
import json
import subprocess


def get_azd_env_values():
    """Get environment values from azd env get-values."""
    try:
        result = subprocess.run(
            ["azd", "env", "get-values"],
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        
        env_values = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                # Handle quoted values
                key, value = line.split('=', 1)
                # Remove surrounding quotes if present
                value = value.strip('"').strip("'")
                env_values[key] = value
        
        return env_values
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get azd environment values: {e}")
        return {}
    except FileNotFoundError:
        print(f"❌ azd CLI not found")
        return {}


def update_appservice_settings(resource_group: str, webapp_name: str, settings: dict):
    """Update App Service application settings."""
    try:
        # Build the settings string for Azure CLI
        settings_args = [f"{k}={v}" for k, v in settings.items()]
        
        cmd = [
            "az", "webapp", "config", "appsettings", "set",
            "--resource-group", resource_group,
            "--name", webapp_name,
            "--settings"
        ] + settings_args
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
        print(f"✅ Updated App Service settings for {webapp_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update App Service settings: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"⚠️  Azure CLI not found, skipping App Service settings update")
        return False


def load_agents_config():
    """Load agent configuration from agents.json."""
    agents_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents.json")
    
    if not os.path.exists(agents_file):
        print("⚠️  agents.json not found")
        return []
    
    with open(agents_file, 'r') as f:
        data = json.load(f)
        # Handle nested structure with "agents" key
        if isinstance(data, dict) and "agents" in data:
            return data["agents"]
        return data if isinstance(data, list) else []


def main():
    print("\n🚀 Post-deploy: Configuring Azure App Service...")
    
    # Get environment values
    env_values = get_azd_env_values()
    
    resource_group = env_values.get("AZURE_RESOURCE_GROUP")
    webapp_name = env_values.get("AZURE_WEBAPP_NAME")
    
    if not resource_group or not webapp_name:
        print("❌ Missing AZURE_RESOURCE_GROUP or AZURE_WEBAPP_NAME")
        print("   Available env values:", list(env_values.keys()))
        return
    
    print(f"📦 Resource Group: {resource_group}")
    print(f"🌐 Web App: {webapp_name}")
    
    # Load agents configuration
    agents = load_agents_config()
    
    if not agents:
        print("⚠️  No agents configured")
        return
    
    # Build environment variables for agents
    agent_settings = {}
    for i, agent in enumerate(agents, 1):
        # Support both "agent_id" and "id" keys
        agent_id = agent.get("agent_id") or agent.get("id")
        model = agent.get("model", "unknown")
        
        if agent_id:
            agent_settings[f"BING_AGENT_ID_{i}"] = agent_id
            agent_settings[f"BING_AGENT_MODEL_{i}"] = model
            print(f"   Agent {i}: {model} -> {agent_id[:20]}...")
    
    if agent_settings:
        update_appservice_settings(resource_group, webapp_name, agent_settings)
    
    print("\n✅ App Service configuration complete!")


if __name__ == "__main__":
    main()
