import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)

# Handle toml loading for Python 3.10 vs 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

VERSION = "0.1.0"

class Config:
    def __init__(self):
        self.default_file_path = Path("tasks.json")
        self.default_project = None
        self.preferred_view = "list"
        self.context = None
        self.auto_context = None
        self.ai_api_key = None
        self.ai_base_url = "https://api.openai.com/v1"
        self.ai_model = "gpt-4o-mini"
        self.load_from_toml()

    def load_from_toml(self):
        config_path = Path.home() / ".task-cli.toml"
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
                    
                cli_config = data.get("task-cli", {})
                
                if "data_path" in cli_config:
                    self.default_file_path = Path(cli_config["data_path"])
                
                if "default_project" in cli_config:
                    self.default_project = cli_config["default_project"]
                    
                if "ai_api_key" in cli_config:
                    self.ai_api_key = cli_config["ai_api_key"]
                if "ai_base_url" in cli_config:
                    self.ai_base_url = cli_config["ai_base_url"]
                if "ai_model" in cli_config:
                    self.ai_model = cli_config["ai_model"]
                    
            except Exception as e:
                print(f"Warning: Failed to parse config file: {e}")

# Global config instance
settings = Config()
DEFAULT_FILE_PATH = settings.default_file_path
