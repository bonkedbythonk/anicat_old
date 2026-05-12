from pathlib import Path
from unittest.mock import patch
import os

# Set up environment
os.environ["PYTHONPATH"] = "."

from anicat_media.cli.config.loader import ConfigLoader

def test_first_run_no_interactive():
    temp_config = Path("scratch/test_first_run_config.toml")
    if temp_config.exists():
        temp_config.unlink()
        
    loader = ConfigLoader(config_path=temp_config)
    
    # This should not prompt and just return the default config
    with patch("click.echo") as mock_echo:
        config = loader.load()
        
        # Verify echo was called with the "Creating default configuration" message
        calls = [call.args[0] for call in mock_echo.call_args_list]
        print("Echo calls:", calls)
        assert any("Creating default configuration" in c for c in calls)
        
    assert temp_config.exists()
    print("SUCCESS: Default config created without interactive prompt.")

if __name__ == "__main__":
    try:
        test_first_run_no_interactive()
    except Exception as e:
        print(f"FAILURE: {e}")
        import traceback
        traceback.print_exc()
