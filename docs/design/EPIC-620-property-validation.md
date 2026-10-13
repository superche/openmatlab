# EPIC-620: property attributes and validation (O-E3)

Criterion **O04** (`m8_o04_property_attributes`) in [M8](../milestones/M8-object-system.md). O04 was already met by the O-E1 class model: Constant, Dependent with `get.`/`set.`, and SetAccess/Access. This epic delivers the rest of the property-attribute scope recorded on #620.

## Property validation
`name (dims) Class {validators} = default`. The spec is parsed in `lang/classdef_parser.py` (`_spec`) into `PropDecl.dims`, `.cls` and `.validators`, and enforced by `PropInfo.validate` in `runtime/classdef.py` in MATLAB order:
1. **Class.** If the value is already the class (or `isa` it, for user classes) it is accepted. Otherwise it is converted with the class function, so `'7'` becomes `55` for double and `65` becomes `'A'` for char. A failed conversion raises `MATLAB:validation:UnableToConvert`.
2. **Size.** `:` is a wildcard. A scalar is expanded to a fully fixed size, and a vector is reshaped to the declared vector orientation. Any other mismatch raises `MATLAB:validation:IncompatibleSize`, "Value must be 1-by-:.".
3. **Validators**, either `f` or `f(Prop, args...)`. The prop-name first argument is optional and the value is passed first. Each failure is reported as "Error setting property 'p' of class 'C'. <validator message>" and keeps the validator's identifier.

Validation runs before a `set.` method, on every assignment including those made in the constructor, and on explicit defaults. A property with a numeric class and no default gets zeros of its fixed size, or an empty value of that class.

## mustBe* functions (`libs/validators.py`)
`mustBePositive`, `mustBeNonnegative`, `mustBeNegative`, `mustBeNonpositive`, `mustBeNonzero`, `mustBeFinite`, `mustBeNonNan`, `mustBeReal`, `mustBeInteger`, `mustBeNumeric`, `mustBeNumericOrLogical`, `mustBeText`, `mustBeNonempty`, `mustBeVector`, `mustBeScalarOrEmpty`, `mustBeMember`, `mustBeInRange` (with exclusive flags), and `mustBeGreaterThan`/`OrEqual`/`mustBeLessThan`/`OrEqual`. Each raises its `MATLAB:validators:<name>` identifier.

## Abstract, immutable, Hidden
- `classdef (Abstract)`, `methods (Abstract)` signatures (parsed by `_signature_name`) and `properties (Abstract)` make a class abstract. `ClassInfo.abstract_members` walks the MRO, so a subclass that leaves something unimplemented is still abstract. Direct instantiation raises `MATLAB:class:abstract`.
- `SetAccess = immutable` is settable only in the constructor; this existed before and is now covered by tests.
- `Hidden` properties are readable but left out of the default display.

## Tests
- `tests/unit/test_classdef_validation.py`
- `features/classdef_validation.feature`

## Residuals
See issue #645.
