import os
from collections.abc import Iterable

from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.util_rules import pex_from_targets
from pants.backend.python.util_rules.pex import (
    PexRequest,
    VenvPexProcess,
    create_pex,
    create_venv_pex,
)
from pants.backend.python.util_rules.pex_from_targets import RequirementsPexRequest
from pants.backend.python.util_rules.python_sources import (
    PythonSourceFilesRequest,
    prepare_python_sources,
)
from pants.core.goals.check import CheckRequest, CheckResult, CheckResults
from pants.core.util_rules import config_files
from pants.core.util_rules.source_files import (
    SourceFilesRequest,
    determine_source_files,
)
from pants.engine.fs import Digest, MergeDigests
from pants.engine.intrinsics import execute_process
from pants.engine.rules import (
    Get,
    collect_rules,
    concurrently,
    implicitly,  # pyright:ignore[reportUnknownVariableType]
    rule,
)
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel
from pants.util.ordered_set import OrderedSet
from pants.util.strutil import pluralize

from pants_basedpyright.partition import BasedPyrightPartition, partition_basedpyright
from pants_basedpyright.request import BasedPyrightRequest
from pants_basedpyright.subsystem import BasedPyright


def determine_python_files(files: Iterable[str]) -> tuple[str, ...]:
    """We run over all .py and .pyi files, but .pyi files take precedence."""
    result: OrderedSet[str] = OrderedSet()
    for f in files:
        if f.endswith(".pyi"):
            py_file = f[:-1]  # That is, strip the `.pyi` suffix to be `.py`.
            result.discard(py_file)
            result.add(f)
        elif f.endswith(".py"):
            pyi_file = f + "i"
            if pyi_file not in result:
                result.add(f)
        else:
            result.add(f)

    return tuple(result)


def _generate_argv(
    source_files: tuple[str, ...],
    python_path: str,
    python_version: str | None,
    basedpyright: BasedPyright,
) -> tuple[str, ...]:
    args: list[str] = []
    args.extend(basedpyright.args)
    args.extend(["--pythonpath", python_path])

    if python_version:
        args.extend(["--pythonversion", python_version])

    if basedpyright.config:
        args.extend(["--project", basedpyright.config])

    args.extend(os.path.join("{chroot}", source_file) for source_file in source_files)
    return tuple(args)


@rule
async def run_basedpyright(
    partition: BasedPyrightPartition,
    basedpyright: BasedPyright,
    python_setup: PythonSetup,
) -> CheckResult:
    root_sources_request = determine_source_files(
        SourceFilesRequest(fs.sources for fs in partition.field_sets)
    )

    closure_sources_get = prepare_python_sources(
        PythonSourceFilesRequest(partition.root_targets.closure()),
        **implicitly(),  # pyright:ignore[reportAny]
    )

    requirements_pex_get = create_pex(
        **implicitly(  # pyright:ignore[reportAny]
            RequirementsPexRequest(
                (fs.address for fs in partition.field_sets),
                hardcoded_interpreter_constraints=partition.interpreter_constraints,
            )
        )
    )

    basedpyright_venv_pex_request = create_venv_pex(
        **implicitly(  # pyright:ignore[reportAny]
            basedpyright.to_pex_request(
                interpreter_constraints=partition.interpreter_constraints
            )
        )
    )

    (
        requirements_pex,
        basedpyright_pex,
        root_sources,
        closure_sources,
        config_files_digest,
    ) = await concurrently(
        requirements_pex_get,
        basedpyright_venv_pex_request,
        root_sources_request,
        closure_sources_get,
        basedpyright.get_config_files(),
    )

    requirements_venv_pex = await create_venv_pex(
        **implicitly(  # pyright:ignore[reportAny]
            PexRequest(
                output_filename="requirements_venv.pex",
                internal_only=True,
                pex_path=[requirements_pex],
                interpreter_constraints=partition.interpreter_constraints,
            )
        )
    )

    input_digest = await Get(
        Digest,
        MergeDigests(
            (
                closure_sources.source_files.snapshot.digest,
                config_files_digest,
                basedpyright_pex.digest,
                requirements_venv_pex.digest,
            )
        ),
    )

    argv = _generate_argv(
        source_files=root_sources.snapshot.files,
        python_path=requirements_venv_pex.python.argv0,
        python_version=partition.interpreter_constraints.minimum_python_version(
            python_setup.interpreter_versions_universe
        ),
        basedpyright=basedpyright,
    )

    env = {
        "PEX_EXTRA_SYS_PATH": ":".join(list(closure_sources.source_roots)),
    }
    result = await execute_process(
        **implicitly(  # pyright:ignore[reportAny]
            VenvPexProcess(
                basedpyright_pex,
                description=f"Run basedpyright on {pluralize(len(root_sources.snapshot.files), 'file')}.",
                argv=argv,
                input_digest=input_digest,
                extra_env=env,
                level=LogLevel.DEBUG,
            ),
        )
    )
    return CheckResult.from_fallible_process_result(
        result,
        partition_description=partition.description,
    )


@rule
async def basedpyright_check(
    request: BasedPyrightRequest,
    basedpyright: BasedPyright,
) -> CheckResults:
    if basedpyright.skip:
        return CheckResults([], checker_name=request.tool_name)

    partitions = await partition_basedpyright(request, **implicitly())  # pyright:ignore[reportAny]
    partitioned_results = await concurrently(
        run_basedpyright(partition, **implicitly())  # pyright:ignore[reportAny]
        for partition in partitions
    )
    return CheckResults(partitioned_results, checker_name=request.tool_name)


def rules():
    return [
        *collect_rules(),
        *config_files.rules(),
        *pex_from_targets.rules(),
        UnionRule(CheckRequest, BasedPyrightRequest),
    ]
