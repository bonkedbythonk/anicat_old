import click
import uvicorn
import webbrowser
from ...core.config import AppConfig

@click.command()
@click.option("--port", default=13370, help="Port to run the API on.")
@click.option("--host", default="127.0.0.1", help="Host to bind the server to. Use 127.0.0.1 for maximum privacy.")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically.")
@click.option("--reload", is_flag=True, help="Enable hot reload on code changes (development mode).")
@click.pass_obj
def dashboard(config: AppConfig, port: int, host: str, no_browser: bool, reload: bool):
    """Launch the Anicat PWA Dashboard."""
    from ...api.main import create_app
    import socket

    app = create_app(config)
    
    # Get local IP for convenience
    local_ip = "localhost"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    click.echo("Anicat Dashboard is starting...")
    click.echo(f"   - Local:  http://localhost:{port}")
    if host == "0.0.0.0" and local_ip != "localhost":
        click.echo(f"   - Remote: http://{local_ip}:{port} (for your iPhone/Tablet)")
    
    if not no_browser:
        import time
        from threading import Timer
        
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
            
        Timer(1, open_browser).start()

    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)
