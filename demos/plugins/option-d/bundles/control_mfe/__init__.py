def mount(shell):
    shell.register_command("step", lambda sys: f"step({sys})")
    return "[ControlMFE] panel=step-response (isolated)"
