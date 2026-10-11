# Option C — Host extension points (slots) + thin adapters

The **host owns** named slots (`commands`, `panels`, `menus`, `toolbar`,
`status`). Plugins are thin adapters that fill slots; domains customize UX
by targeting the same slots (no forked shell).

Discovery can be anything (entry points, YAML path, hard-wired for this demo).
The architecture bet is **stable slot contracts**, not how plugins are found.
