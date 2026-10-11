def register(registry):
    registry["bode"] = lambda sys: f"bode({sys})"
    registry["fft"] = lambda x: f"fft({x})"
