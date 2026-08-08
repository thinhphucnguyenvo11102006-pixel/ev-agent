"""
E.V. Shell Executor — PowerShell/CMD command execution.
"""

import subprocess
import logging

import config

logger = logging.getLogger("ev.tools.shell_executor")


def execute_shell(command: str, shell: str = "powershell") -> str:
    """
    Execute a shell command via PowerShell or CMD.
    Returns stdout + stderr output.
    """
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    # Safety check
    check = guardrail.check_shell_command(command)
    if not check.allowed:
        return check.reason

    # Rate limit check
    rate_check = guardrail.check_rate_limit("execute_shell")
    if not rate_check.allowed:
        return rate_check.reason

    if check.requires_confirmation:
        logger.warning(f"Sensitive command detected: {command}")
        # In a full implementation, this would ask for user confirmation
        # For now, proceed with a warning in the output
        warning = f"⚠️ Warning: {check.reason}\n"
    else:
        warning = ""

    try:
        if shell == "powershell":
            cmd = ["powershell", "-NoProfile", "-Command", command]
        else:
            cmd = ["cmd", "/c", command]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.TOOL_EXECUTION_TIMEOUT,
            cwd=str(config.PROJECT_ROOT),
        )

        output = warning
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"

        return output.strip() or "Command executed successfully (no output)."

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {config.TOOL_EXECUTION_TIMEOUT} seconds."
    except Exception as e:
        return f"Error executing command: {e}"
