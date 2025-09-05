from typing import final

from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import ConsoleScript
from pants.core.goals.resolves import ExportableTool
from pants.core.util_rules.config_files import ConfigFilesRequest, find_config_file
from pants.engine.fs import Digest, MergeDigests
from pants.engine.rules import Get, collect_rules, concurrently
from pants.engine.unions import UnionRule
from pants.option.option_types import ArgsListOption, BoolOption, FileOption, SkipOption
from pants.util.strutil import softwrap


@final
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
    default_lockfile_resource = ("pants_basedpyright", "basedpyright.lock")

    config = FileOption(
        default=None,
        advanced=True,
        help=softwrap(
            """
            Path to pyrightconfig.json or pyproject.toml file with [tool.basedpyright] or [tool.pyright] section
            (https://docs.basedpyright.com/latest/configuration/config-files/).
            """
        ),
    )

    config_discovery = BoolOption(
        default=True,
        advanced=True,
        help=softwrap(
            """
            If true, Pants will include any relevant pyrightconfig.json and pyproject.toml config files during runs.

            Use `[basedpyright].config` instead if your config is in a non-standard location.
            """
        ),
    )

    async def get_config_files(self) -> Digest:
        """Get all possible config files for basedpyright.

        https://docs.basedpyright.com/latest/configuration/config-files

        Because basedpyright supports pyrightconfig.json and two separate
        config sections in pyproject.toml ([tool.basedpyright] and [tool.pyright]),
        we need run two separate ConfigFilesRequests since check_content is a
        dictionary mapping source files to their expected content.
        """
        config_request = ConfigFilesRequest(
            specified=self.config,
            specified_option_name=f"[{self.options_scope}].config",
            discovery=self.config_discovery,
            check_existence=["pyrightconfig.json"],
            check_content={"pyproject.toml": b"[tool.basedpyright"},
        )

        config_request_pyright = ConfigFilesRequest(
            discovery=self.config_discovery,
            check_content={"pyproject.toml": b"[tool.pyright"},
        )

        config_files, config_files_pyright = await concurrently(
            find_config_file(config_request),
            find_config_file(config_request_pyright),
        )

        return await Get(
            Digest,
            MergeDigests(
                (config_files.snapshot.digest, config_files_pyright.snapshot.digest)
            ),
        )


def rules():
    return [
        *collect_rules(),
        UnionRule(ExportableTool, BasedPyright),
    ]
