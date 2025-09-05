from dataclasses import dataclass

from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.util_rules.interpreter_constraints import (
    InterpreterConstraints,
)
from pants.backend.python.util_rules.partition import (
    _partition_by_interpreter_constraints_and_resolve,  # pyright:ignore[reportPrivateUsage]
)
from pants.engine.collection import Collection
from pants.engine.internals.graph import coarsened_targets as coarsened_targets_get
from pants.engine.rules import (
    collect_rules,
    implicitly,  # pyright:ignore[reportUnknownVariableType]
    rule,
)
from pants.engine.target import CoarsenedTargets, CoarsenedTargetsRequest
from pants.util.ordered_set import FrozenOrderedSet, OrderedSet

from pants_basedpyright.fieldset import BasedPyrightFieldSet
from pants_basedpyright.request import BasedPyrightRequest
from pants_basedpyright.subsystem import BasedPyright


@dataclass(frozen=True)
class BasedPyrightPartition:
    field_sets: FrozenOrderedSet[BasedPyrightFieldSet]
    root_targets: CoarsenedTargets
    resolve_description: str | None
    interpreter_constraints: InterpreterConstraints

    @property
    def description(self) -> str:
        ics = str(sorted(str(c) for c in self.interpreter_constraints))
        return f"{self.resolve_description}, {ics}" if self.resolve_description else ics


class BasedPyrightPartitions(Collection[BasedPyrightPartition]):
    pass


@rule
async def partition_basedpyright(
    request: BasedPyrightRequest,
    python_setup: PythonSetup,
    basedpyright: BasedPyright,
) -> BasedPyrightPartitions:
    resolve_and_interpreter_constraints_to_field_sets = (
        _partition_by_interpreter_constraints_and_resolve(
            request.field_sets, python_setup
        )
    )

    coarsened_targets = await coarsened_targets_get(
        CoarsenedTargetsRequest(field_set.address for field_set in request.field_sets),
        **implicitly(),  # pyright:ignore[reportAny]
    )
    coarsened_targets_by_address = coarsened_targets.by_address()

    return BasedPyrightPartitions(
        BasedPyrightPartition(
            FrozenOrderedSet(field_sets),
            CoarsenedTargets(
                OrderedSet(
                    coarsened_targets_by_address[field_set.address]
                    for field_set in field_sets
                ),
            ),
            resolve if len(python_setup.resolves) > 1 else None,
            interpreter_constraints or basedpyright.interpreter_constraints,
        )
        for (
            resolve,
            interpreter_constraints,
        ), field_sets in resolve_and_interpreter_constraints_to_field_sets.items()
    )


def rules():
    return [
        *collect_rules(),
    ]
