from dataclasses import dataclass
from typing import final

from pants.backend.python.target_types import (
    InterpreterConstraintsField,
    PythonResolveField,
    PythonSourceField,
)
from pants.engine.target import FieldSet, Target

from pants_basedpyright.skip_field import SkipBasedPyrightField


@final
@dataclass(frozen=True)
class BasedPyrightFieldSet(FieldSet):
    required_fields = (PythonSourceField,)
    sources: PythonSourceField
    resolve: PythonResolveField
    interpreter_constraints: InterpreterConstraintsField

    @classmethod
    def opt_out(cls, tgt: Target) -> bool:
        return tgt.get(SkipBasedPyrightField).value
