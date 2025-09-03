from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import ConsoleScript
from pants.core.goals.resolves import ExportableTool
from pants.engine.rules import collect_rules
from pants.engine.unions import UnionRule
from pants.option.option_types import ArgsListOption, SkipOption


class BasedPyright(PythonToolBase):
    """Checker for BasedPyright."""

    options_scope = "basedpyright"
    name = "basedpyright"
    help_short = "The basedpyright type checker (https://docs.basedpyright.com/)"

    skip = SkipOption("lint")
    args = ArgsListOption(example="--level <LEVEL>")
    register_interpreter_constraints = True

    default_version = "v1.31.3"
    default_main = ConsoleScript("basedpyright")
    default_requirements = ["basedpyright>=1.31.3"]
    default_interpreter_constraints = ["CPython>=3.7"]
    default_lockfile_resource = ("pants-basedpyright", "basedpyright.lock")


def rules():
    return [
        *collect_rules(),
        UnionRule(ExportableTool, BasedPyright),
    ]
