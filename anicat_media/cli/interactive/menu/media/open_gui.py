import webbrowser
import time
import subprocess
import sys
import os
import socket
from threading import Thread, Timer
from rich import print as rprint
from ...session import Context, session
from ...state import InternalDirective, State
from anicat_media.core.theme import ICONS

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

@session.menu
def open_gui(ctx: Context, state: State) -> State | InternalDirective:
    """Action to launch the Anicat GUI."""
    icons = ctx.config.general.icons
    port = 8000
    
    if is_port_in_use(port):
        rprint(f"\n[bold green]{ICONS.get('BROWSER', icons)}Anicat Dashboard is already running![/]")
        rprint(f"[dim]Opening http://localhost:{port} in your browser...[/]")
        webbrowser.open(f"http://localhost:{port}")
        ctx.feedback.pause_for_user("return to main menu")
        return InternalDirective.MAIN

    rprint(f"\n[bold magenta]{ICONS.get('BROWSER', icons)}Starting Anicat Dashboard Server...[/]")
    rprint(f"[dim]This will launch a background process to serve the web interface.[/]")
    
    try:
        # We use 'uv run' to ensure the environment is correct and dependencies are found
        # We point directly to the cli script since __main__ might be tricky in some environments
        # Finding the project root to run 'uv run' correctly
        from pathlib import Path
        project_root = str(Path(__file__).resolve().parents[5])
        
        # Command to run via uv
        cmd = ["uv", "run", "anicat", "dashboard", "--no-browser"]
        
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            start_new_session=True
        )
        
        rprint("[bold yellow]Server starting via UV...[/]")
        
        def launch():
            # Wait for server to actually start
            for _ in range(15): # Increased timeout for UV environment setup
                if is_port_in_use(port):
                    webbrowser.open(f"http://localhost:{port}")
                    return
                time.sleep(1)
            rprint("[bold red]Server took too long to start. Please try running 'anicat dashboard' manually.[/]")
            
        Thread(target=launch, daemon=True).start()
        
        rprint("\n[bold green]Dashboard launch initiated![/]")
        rprint(f"[dim]Link: http://localhost:{port}[/]")
        
    except Exception as e:
        rprint(f"[bold red]Failed to start dashboard: {e}[/bold red]")
    
    ctx.feedback.pause_for_user("return to main menu")
    return InternalDirective.MAIN
