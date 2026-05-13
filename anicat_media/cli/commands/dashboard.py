import click
import uvicorn
import webbrowser
import multiprocessing
import os
import signal
from ...core.config import AppConfig

@click.command()
@click.option("--port", default=8000, help="Port to run the API on.")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically.")
@click.pass_obj
def dashboard(config: AppConfig, port: int, no_browser: bool):
    """Launch the Anicat PWA Dashboard."""
    from ...api.main import app
    
    click.echo(f"Starting Anicat API on http://localhost:{port}")
    
    if not no_browser:
        # Give the server a moment to start
        import time
        from threading import Timer
        
        def open_browser():
            time.sleep(1.5)
            # We now serve the frontend directly from the backend on port 8000
            click.echo("Opening Anicat Dashboard...")
            webbrowser.open(f"http://localhost:8000")
            
        Timer(1, open_browser).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
