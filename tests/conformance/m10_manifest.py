"""M10 (Tables and data types) conformance manifest. Single source for the exit criteria.

Same honesty model as M8: ``pending`` criteria run as strict xfail and flip to ``met``
in the PR that makes them pass (manifest + docs/milestones/M10-tables.md together).
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "T01": ("m10_t01_table_construct_display", "p0", [691], "pending"),
    "T02": ("m10_t02_table_indexing", "p0", [691], "pending"),
    "T03": ("m10_t03_table_conversion_varfun", "p1", [693], "pending"),
    "T04": ("m10_t04_categorical", "p0", [692], "pending"),
    "T05": ("m10_t05_sortrows_sets", "p1", [693, 585], "pending"),
    "T06": ("m10_t06_joins", "p1", [696], "pending"),
    "T07": ("m10_t07_grouping", "p1", [696], "pending"),
    "T08": ("m10_t08_readtable_writetable", "p0", [694, 577], "pending"),
    "T09": ("m10_t09_datetime_arrays", "p1", [695, 602, 673], "pending"),
    "T10": ("m10_t10_timetable", "p2", [697], "pending"),
}
