#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read model pool configuration from .env and set azd environment parameters.
This allows Bicep to dynamically deploy only the required models.
"""
import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def read_env_file():
    """Read .env file and extract AGENT_POOL_SIZE_* values."""
    env_file = Path(".env")
    if not env_file.exists():
        print("[WARNING] .env file not found, using defaults (all models disabled)")
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
    print("Reading Model Configuration from .env")
    print("=" * 80)
    print()
    
    # Read configuration
    config = read_env_file()
    
    # Map env var names to Bicep parameter names (camelCase)
    # ONLY officially supported models: GPT-4o, GPT-4, GPT-3.5-Turbo
    param_mapping = {
        'AGENT_POOL_SIZE_GPT4O': 'agentPoolSizeGpt4o',
        'AGENT_POOL_SIZE_GPT4': 'agentPoolSizeGpt4',
        'AGENT_POOL_SIZE_GPT4_TURBO': 'agentPoolSizeGpt4Turbo',
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
