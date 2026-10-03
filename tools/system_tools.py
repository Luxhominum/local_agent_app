import subprocess
import psutil
import os
import platform
from typing import Dict, Any

DANGEROUS_KEYWORDS = [
    "format", "del /f", "remove-item -recurse -force", "rmdir /s /q", 
    "shutdown", "restart-computer", "stop-computer", "reg delete",
    "diskpart", "bcdedit", "net user"
]

def get_system_metrics() -> Dict[str, Any]:
    """Retrieves current CPU, RAM, Disk usage and OS info."""
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\' if os.name == 'nt' else '/')
        cpu_pct = psutil.cpu_percent(interval=0.2)
        
        return {
            "os": platform.platform(),
            "cpu_percent": cpu_pct,
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": disk.percent
        }
    except Exception as e:
        return {"error": str(e)}

def format_system_metrics_text() -> str:
    """Returns a clean formatted string of system vitals."""
    m = get_system_metrics()
    if "error" in m:
        return f"Error reading system metrics: {m['error']}"
        
    return (
        f"System Status:\n"
        f"- OS: {m['os']}\n"
        f"- CPU Usage: {m['cpu_percent']}%\n"
        f"- RAM: {m['ram_used_gb']} GB / {m['ram_total_gb']} GB ({m['ram_percent']}%)\n"
        f"- C: Drive: {m['disk_free_gb']} GB free out of {m['disk_total_gb']} GB ({m['disk_percent']}% used)"
    )

def execute_powershell(command: str, confirmed: bool = False) -> str:
    """Executes a PowerShell command with safety guardrails for destructive commands."""
    cmd_lower = command.lower().strip()
    
    # Check for destructive commands requiring user confirmation
    for danger in DANGEROUS_KEYWORDS:
        if danger in cmd_lower and not confirmed:
            return (
                f"SAFETY_REQUIRED: The command `{command}` contains potentially destructive operations (`{danger}`). "
                f"Please confirm execution to proceed."
            )
            
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        output = res.stdout.strip()
        if res.returncode != 0:
            err = res.stderr.strip()
            return f"Command exited with code {res.returncode}:\n{err}\n{output}"
            
        return output if output else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 45 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"
