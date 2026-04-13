from pathlib import Path
from .core.config import load_config, get_config

def list_environments(config_path="phoenix.yaml"):
    """Lists all environments from the config file."""
    print(f"Listing environments from {config_path}")

    try:
        config_file = Path(config_path)
        if config_file.exists():
            config = load_config(config_file)
        else:
            # Try configs/phoenix.yaml as fallback
            fallback_path = Path("configs/phoenix.yaml")
            if fallback_path.exists():
                config = load_config(fallback_path)
            else:
                config = get_config()

        environments = list(config.environments.keys())
        for env_name in environments:
            env_config = config.environments[env_name]
            print(f"  {env_name}: {env_config.base_url}")
            if env_config.description:
                print(f"    Description: {env_config.description}")

        return environments
    except Exception as e:
        print(f"Error loading environments: {e}")
        return []
