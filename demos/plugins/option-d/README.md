# Option D — Micro-frontend-ish UI plugins (optional)

Each UI plugin is an **isolated bundle** (own render function / fake "mount")
composed by a shell. Domains ship a domain core + optional UI bundle.
Communication is message-bus style (no shared widget tree).

Useful if OpenMATLAB grows a **web** workbench; heavier than needed for a
local Python desktop today.
