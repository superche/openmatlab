"""Char / string MVP value (double-quoted literals, which/addpath results)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharValue:
    """Minimal MATLAB-like char/string carrier (not an Array)."""

    text: str

    def matlab_class(self) -> str:
        return "char"

    def __str__(self) -> str:
        return self.text
