def mount(shell):
    # Domain API lives beside the UI bundle
    shell.register_command("fft", lambda x: f"fft({x})")

    def on_fft(payload):
        # Isolated UI reacts via bus — no shared widget imports
        shell.mounts.append(f"[SignalMFE] spectrum for {payload.get('x')}")

    shell.bus.on("domain.signal.fft", on_fft)
    # Domain customizes UX by emitting layout preference messages
    shell.bus.emit("ui.layout", {"prefer": "spectrum-right"})
    return "[SignalMFE] panel=spectrum (isolated)"
