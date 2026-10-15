"""M8 (Object system) conformance manifest. This is the single source for the exit criteria.

It follows the same honesty model as M2/M7. ``pending`` criteria run as strict xfail,
which turns into a failure once they pass, so the manifest and the milestone doc must
be updated in the PR that makes a criterion pass. Each script writes its class files
into a temporary folder on the path.
"""

from __future__ import annotations

# id -> (script, priority, tracking issues, status)
CRITERIA = {
    "O01": ("m8_o01_value_class", "p0", [618], "met"),
    "O02": ("m8_o02_handle_class", "p0", [619], "met"),
    "O03": ("m8_o03_inheritance", "p0", [619], "met"),
    "O04": ("m8_o04_property_attributes", "p1", [620, 618], "met"),
    "O05": ("m8_o05_static_packages", "p1", [622], "met"),
    "O06": ("m8_o06_operator_overloading", "p1", [621], "met"),
    "O07": ("m8_o07_subsref_subsasgn", "p1", [621], "met"),
    "O08": ("m8_o08_enumerations", "p1", [622], "met"),
    "O09": ("m8_o09_introspection", "p1", [622], "met"),
    "O10": ("m8_o10_display_dot_objects", "p1", [621, 623, 593, 602], "pending"),
}
