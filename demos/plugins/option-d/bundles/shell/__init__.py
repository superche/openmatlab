def mount(shell):
    shell.bus.on("ui.toast", lambda p: None)  # shell owns chrome
    return "[ShellChrome] menu|toolbar|status"
