from dataclasses import dataclass

from pants.backend.python.target_types import (
    InterpreterConstraintsField,
    PythonResolveField,
    PythonSourceField,
)
from pants.engine.target import FieldSet, Target

from .skip_field import SkipBasedPyrightField


@dataclass(frozen=True)
class BasedPyrightFieldSet(FieldSet):
    required_fields = (PythonSourceField,)
    sources: PythonSourceField
    resolve: PythonResolveField
    interpreter_constraints: InterpreterConstraintsField

    @classmethod
    def opt_out(cls, tgt: Target) -> bool:
        return tgt.get(SkipBasedPyrightField).value
