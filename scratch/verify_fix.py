import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up environment
os.environ["PYTHONPATH"] = "."

from anicat_media.core.config import AppConfig
import anicat_media.cli.commands.login as login_module
from anicat_media.core.constants import USER_CONFIG

def test_login_flow_updates_config():
    temp_config = Path("scratch/temp_config.toml")
    temp_config.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy config file without anilist section
    temp_config.write_text("[general]\nwelcome_screen = true\n", encoding="utf-8")
    
    # Create an AppConfig object (it will have default anilist.token = "")
    config = AppConfig()
    
    # Mock external calls and USER_CONFIG
    with patch("click.launch"), \
         patch("subprocess.run"), \
         patch("builtins.input", return_value=""), \
         patch("anicat_media.cli.commands.login.USER_CONFIG", temp_config), \
         patch("anicat_media.cli.commands.login.ConfigLoader") as mock_loader:
        
        # Mock loader.load() to return a config with a token (simulating user edit)
        mock_instance = mock_loader.return_value
        config_with_token = AppConfig()
        config_with_token.anilist.token = "test_token"
        mock_instance.load.return_value = config_with_token
        
        # Run login_flow
        login_module.login_flow(config)
        
    # Check if the config file now contains the anilist section and token field
    content = temp_config.read_text(encoding="utf-8")
    print("Config file content after login_flow:")
    print(content)
    
    assert "[anilist]" in content
    assert 'token = ""' in content
    print("\nSUCCESS: [anilist] section and token field were added to the config file.")

if __name__ == "__main__":
    try:
        test_login_flow_updates_config()
    except Exception as e:
        print(f"\nFAILURE: {e}")
        import traceback
        traceback.print_exc()
