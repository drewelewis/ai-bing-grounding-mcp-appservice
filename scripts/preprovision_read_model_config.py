#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read model pool configuration from agents.config.json (or .env fallback) and set azd environment parameters.
This allows Bicep to dynamically deploy only the required models.

Configuration sources (in priority order):
1. agents.config.json - Checked into repo, safe for CI/CD
2. .env file - Local overrides (not checked in)
"""
import os
import sys
import json
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def read_config_json():
    """Read agents.config.json file and extract model pool sizes."""
    config_file = Path("agents.config.json")
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = {}
        models = data.get('models', {})
        
        # Map model names to env var format
        model_mapping = {
            'gpt-4o': 'AGENT_POOL_SIZE_GPT4O',
            'gpt-4.1-mini': 'AGENT_POOL_SIZE_GPT41_MINI',
            'gpt-4': 'AGENT_POOL_SIZE_GPT4',
            'gpt-35-turbo': 'AGENT_POOL_SIZE_GPT35_TURBO',
            'gpt-3.5-turbo': 'AGENT_POOL_SIZE_GPT35_TURBO',
        }
        
        for model_name, settings in models.items():
            if settings.get('enabled', False):
                env_key = model_mapping.get(model_name)
                if env_key:
                    config[env_key] = settings.get('agentPoolSize', 0)
        
        return config
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[WARNING] Error reading agents.config.json: {e}")
        return None


def read_env_file():
    """Read .env file and extract AGENT_POOL_SIZE_* values (fallback)."""
    env_file = Path(".env")
    if not env_file.exists():
        return {}
    
    config = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('AGENT_POOL_SIZE_'):
                try:
                    key, value = line.split('=', 1)
                    # Remove inline comments (anything after #)
                    value = value.split('#')[0].strip()
                    config[key] = int(value)
                except (ValueError, IndexError):
                    continue
    return config


def set_azd_env(key, value):
    """Set azd environment variable using azd env set command."""
    import subprocess
    try:
        subprocess.run(['azd', 'env', 'set', key, str(value)], 
                      check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Failed to set {key}: {e.stderr}")


def main():
    print("=" * 80)
    print("Reading Model Configuration")
    print("=" * 80)
    print()
    
    # Try agents.config.json first, then fall back to .env
    config = read_config_json()
    if config is not None:
        print("📄 Using agents.config.json")
    else:
        config = read_env_file()
        if config:
            print("📄 Using .env file (fallback)")
        else:
            print("⚠️  No configuration found (agents.config.json or .env)")
            print("   Creating default agents.config.json would enable model deployment")
            config = {}
    
    print()
    
    # Map env var names to Bicep parameter names (camelCase)
    param_mapping = {
        'AGENT_POOL_SIZE_GPT4O': 'agentPoolSizeGpt4o',
        'AGENT_POOL_SIZE_GPT41_MINI': 'agentPoolSizeGpt41',  # Maps to gpt-4.1 in Bicep
        'AGENT_POOL_SIZE_GPT4': 'agentPoolSizeGpt4',
        'AGENT_POOL_SIZE_GPT35_TURBO': 'agentPoolSizeGpt35Turbo',
    }
    
    print("Setting azd environment parameters for model deployments:")
    print()
    
    for env_key, param_name in param_mapping.items():
        value = config.get(env_key, 0)
        set_azd_env(param_name, value)
        status = "✅ DEPLOY" if value > 0 else "⏭️  SKIP"
        model_name = env_key.replace('AGENT_POOL_SIZE_', '').replace('_', '-').lower()
        print(f"  {status} {model_name}: {value} agents")
    
    print()
    print("✅ Model configuration parameters set successfully!")
    print()


if __name__ == '__main__':
    main()
