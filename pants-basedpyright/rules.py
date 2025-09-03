from dataclasses import dataclass

from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.util_rules import pex_from_targets
from pants.backend.python.util_rules.interpreter_constraints import (
    InterpreterConstraints,
)
from pants.backend.python.util_rules.partition import (
    _partition_by_interpreter_constraints_and_resolve,
)
from pants.backend.python.util_rules.pex import VenvPexProcess, create_venv_pex
from pants.backend.python.util_rules.pex_environment import PexEnvironment
from pants.backend.python.util_rules.python_sources import (
    PythonSourceFilesRequest,
    prepare_python_sources,
)
from pants.core.goals.lint import (
    AbstractLintRequest,
    LintResult,
    Partitions,
)
from pants.core.util_rules.partitions import Partition
from pants.engine.fs import Digest, MergeDigests
from pants.engine.internals.graph import coarsened_targets as coarsened_targets_get
from pants.engine.intrinsics import (
    execute_process,
)
from pants.engine.rules import (
    Get,
    collect_rules,
    concurrently,
    implicitly,
    rule,
)
from pants.engine.target import CoarsenedTargets, CoarsenedTargetsRequest
from pants.util.logging import LogLevel
from pants.util.strutil import pluralize

from .fieldset import BasedPyrightFieldSet
from .request import BasedPyrightRequest
from .subsystem import BasedPyright


@dataclass(frozen=True)
class PartitionMetadata:
    coarsened_targets: CoarsenedTargets
    resolve_description: str | None
    interpreter_constraints: InterpreterConstraints

    @property
    def description(self) -> str:
        ics = str(sorted(str(c) for c in self.interpreter_constraints))
        return f"{self.resolve_description}, {ics}" if self.resolve_description else ics


def generate_argv(
    field_sets: tuple[BasedPyrightFieldSet, ...], basedpyright: BasedPyright
) -> tuple[str, ...]:
    args = []
    args.extend(basedpyright.args)
    args.extend(field_set.source.file_path for field_set in field_sets)
    return tuple(args)


async def _run_basedpyright(
    request: AbstractLintRequest.Batch[BasedPyrightFieldSet, PartitionMetadata],
    basedpyright: BasedPyright,
    pex_environment: PexEnvironment,
) -> LintResult:
    # The coarsened targets in the incoming request are for all targets in the request's original
    # partition. Since the core `lint` logic re-batches inputs according to `[lint].batch_size`,
    # this could be many more targets than are actually needed to lint the specific batch of files
    # received by this rule. Subset the CTs one more time here to only those that are relevant.
    all_coarsened_targets_by_address = request.partition_metadata.coarsened_targets.by_address()
    coarsened_targets = CoarsenedTargets(
        all_coarsened_targets_by_address[field_set.address] for field_set in request.elements
    )
    coarsened_closure = tuple(coarsened_targets.closure())

    basedpyright_venv_pex_request = create_venv_pex(**implicitly(basedpyright.to_pex_request()))

    sources_request = prepare_python_sources(
        PythonSourceFilesRequest(coarsened_closure), **implicitly()
    )

    basedpyright_pex, sources = await concurrently(basedpyright_venv_pex_request, sources_request)

    input_digest = await Get(
        Digest,
        MergeDigests((basedpyright_pex.digest, sources.source_files.snapshot.digest)),
    )

    pythonpath = list(sources.source_roots)
    result = await execute_process(
        **implicitly(
            VenvPexProcess(
                basedpyright_pex,
                description=f"Run basedpyright on {pluralize(len(request.elements), 'file')}.",
                argv=generate_argv(request.elements, basedpyright),
                input_digest=input_digest,
                extra_env={"PEX_EXTRA_SYS_PATH": ":".join(pythonpath)},
                level=LogLevel.DEBUG,
            ),
        )
    )
    return LintResult.create(request, result)


@rule
async def partition_basedpyright(
    request: BasedPyrightRequest.PartitionRequest[BasedPyrightFieldSet],
    basedpyright: BasedPyright,
    python_setup: PythonSetup,
) -> Partitions:
    resolve_and_interpreter_constraints_to_field_sets = (
        _partition_by_interpreter_constraints_and_resolve(request.field_sets, python_setup)
    )

    coarsened_targets = await coarsened_targets_get(
        CoarsenedTargetsRequest(field_set.address for field_set in request.field_sets),
        **implicitly(),
    )
    coarsened_targets_by_address = coarsened_targets.by_address()

    return Partitions(
        Partition(
            tuple(field_sets),
            PartitionMetadata(
                CoarsenedTargets(
                    coarsened_targets_by_address[field_set.address] for field_set in field_sets
                ),
                resolve if len(python_setup.resolves) > 1 else None,
                InterpreterConstraints.merge((basedpyright.interpreter_constraints,)),
            ),
        )
        for (
            resolve,
            _,
        ), field_sets in resolve_and_interpreter_constraints_to_field_sets.items()
    )


@rule
async def basedpyright_lint(
    request: BasedPyrightRequest.Batch,
    basedpyright: BasedPyright,
    pex_environment: PexEnvironment,
) -> LintResult:
    return await _run_basedpyright(request, basedpyright, pex_environment)


def rules():
    return [
        *collect_rules(),
        *BasedPyrightRequest.rules(),
        *pex_from_targets.rules(),
    ]
