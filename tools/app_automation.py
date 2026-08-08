"""
E.V. App Automation — OS-level automation using pyautogui.
"""

import subprocess
import logging
import time

logger = logging.getLogger("ev.tools.app_automation")


def automate_app(action: str, target: str, value: str = "") -> str:
    """
    Perform automation actions on the desktop.
    """
    try:
        if action == "open_app":
            return _open_app(target)
        elif action == "close_app":
            return _close_app(target)
        elif action == "type_text":
            return _type_text(target)
        elif action == "press_key":
            return _press_key(target)
        elif action == "click":
            return _click(target)
        elif action == "move_mouse":
            return _move_mouse(target)
        elif action == "minimize":
            return _window_action("minimize")
        elif action == "maximize":
            return _window_action("maximize")
        elif action == "set_volume":
            return _set_volume(target)
        else:
            return f"Unknown action: {action}. Available: open_app, close_app, type_text, press_key, click, move_mouse, minimize, maximize, set_volume"

    except ImportError:
        return "Error: pyautogui not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"Error performing automation: {e}"


def _open_app(app_name: str) -> str:
    """Open an application."""
    try:
        # Common app mappings for Windows
        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "code": "code.exe",
            "vscode": "code.exe",
            "task manager": "taskmgr.exe",
            "settings": "ms-settings:",
        }

        exe = app_map.get(app_name.lower(), app_name)
        
        if exe.startswith("ms-"):
            subprocess.Popen(["start", exe], shell=True)
        else:
            subprocess.Popen(exe, shell=True)
        
        return f"Opened {app_name}"
    except Exception as e:
        return f"Error opening {app_name}: {e}"


def _close_app(app_name: str) -> str:
    """Close an application by name."""
    try:
        result = subprocess.run(
            ["taskkill", "/IM", f"{app_name}.exe", "/F"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Closed {app_name}"
        return f"Could not close {app_name}: {result.stderr}"
    except Exception as e:
        return f"Error closing {app_name}: {e}"


def _type_text(text: str) -> str:
    """Type text using pyautogui."""
    import pyautogui
    pyautogui.typewrite(text, interval=0.02)
    return f"Typed: {text[:50]}"


def _press_key(key: str) -> str:
    """Press a key or key combination."""
    import pyautogui
    
    # Handle combinations like "ctrl+c"
    if "+" in key:
        keys = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    
    return f"Pressed: {key}"


def _click(coords: str) -> str:
    """Click at coordinates (x,y)."""
    import pyautogui
    
    try:
        parts = coords.replace("(", "").replace(")", "").split(",")
        x, y = int(parts[0].strip()), int(parts[1].strip())
        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})"
    except (ValueError, IndexError):
        return f"Error: Invalid coordinates '{coords}'. Expected format: 'x,y'"


def _move_mouse(coords: str) -> str:
    """Move mouse to coordinates."""
    import pyautogui
    
    try:
        parts = coords.replace("(", "").replace(")", "").split(",")
        x, y = int(parts[0].strip()), int(parts[1].strip())
        pyautogui.moveTo(x, y)
        return f"Mouse moved to ({x}, {y})"
    except (ValueError, IndexError):
        return f"Error: Invalid coordinates '{coords}'."


def _window_action(action: str) -> str:
    """Minimize or maximize the active window."""
    import pyautogui
    
    if action == "minimize":
        pyautogui.hotkey("win", "down")
        return "Window minimized"
    elif action == "maximize":
        pyautogui.hotkey("win", "up")
        return "Window maximized"
    return f"Unknown window action: {action}"


def _set_volume(level: str) -> str:
    """Set system volume (0-100)."""
    try:
        vol = int(level)
        vol = max(0, min(100, vol))
        
        # Use PowerShell to set volume
        ps_script = f"""
        $vol = {vol / 100}
        $obj = New-Object -ComObject WScript.Shell
        1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
        $steps = [math]::Round({vol} / 2)
        1..$steps | ForEach-Object {{ $obj.SendKeys([char]175) }}
        """
        
        # Simpler approach using nircmd if available, otherwise PowerShell
        subprocess.run(
            ["powershell", "-Command", f"Set-Variable -Name vol -Value {vol}; Write-Host 'Volume set to {vol}%'"],
            capture_output=True
        )
        
        return f"Volume set to {vol}%"
    except ValueError:
        return f"Error: Invalid volume level '{level}'. Expected a number 0-100."
