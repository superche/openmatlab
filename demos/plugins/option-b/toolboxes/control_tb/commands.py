def register(registry):
    registry["tf"] = lambda num, den: f"tf({num},{den})"
    registry["step"] = lambda sys: f"step({sys})"
