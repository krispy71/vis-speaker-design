import subprocess


class ClaudeError(Exception):
    pass


def run_claude(prompt: str, timeout: int = 120) -> str:
    """
    Run `claude -p <prompt>` and return the response text.
    Raises ClaudeError on non-zero exit or timeout.
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"Claude CLI timed out after {timeout}s")

    if result.returncode != 0:
        raise ClaudeError(result.stderr.strip() or "Claude CLI returned non-zero exit code")

    return result.stdout.strip()
