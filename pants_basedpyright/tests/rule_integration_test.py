from textwrap import dedent

import pytest
from pants.backend.python import target_types_rules
from pants.backend.python.dependency_inference import (
    rules as dependency_inference_rules,
)
from pants.backend.python.target_types import (
    PythonRequirementTarget,
    PythonSourcesGeneratorTarget,
    PythonSourceTarget,
)
from pants.core.goals.check import CheckResult, CheckResults
from pants.core.util_rules import config_files
from pants.engine.addresses import Address
from pants.engine.fs import EMPTY_DIGEST
from pants.engine.rules import QueryRule
from pants.engine.target import Target
from pants.testutil.python_interpreter_selection import all_major_minor_python_versions
from pants.testutil.python_rule_runner import PythonRuleRunner

from pants_basedpyright.fieldset import BasedPyrightFieldSet
from pants_basedpyright.partition import BasedPyrightPartitions
from pants_basedpyright.request import BasedPyrightRequest
from pants_basedpyright.rules import rules as basedpyright_rules
from pants_basedpyright.subsystem import BasedPyright
from pants_basedpyright.subsystem import rules as basedpyright_subsystem_rules


@pytest.fixture
def rule_runner() -> PythonRuleRunner:
    return PythonRuleRunner(
        rules=[
            *basedpyright_rules(),
            *basedpyright_subsystem_rules(),
            *dependency_inference_rules.rules(),
            *config_files.rules(),
            *target_types_rules.rules(),
            QueryRule(CheckResults, (BasedPyrightRequest,)),
            QueryRule(BasedPyrightPartitions, (BasedPyrightRequest,)),
        ],
        target_types=[
            PythonSourcesGeneratorTarget,
            PythonRequirementTarget,
            PythonSourceTarget,
        ],
    )


PACKAGE = "src/py/project"
GOOD_FILE = dedent(
    """\
    def add(x: int, y: int) -> int:
        return x + y

    result = add(3, 3)
    """
)
BAD_FILE = dedent(
    """\
    def add(x: int, y: int) -> int:
        return x + y

    result = add(2.0, 3.0)
    """
)

# This will fail if `reportUnusedVariable` unless reportUnusedVariable=<false|warning>
NEEDS_CONFIG_FILE = dedent(
    """\
    def my_function():
        unused_variable = 10
    """
)

UNUSED_VARIABLE_JSON_CONFIG = dedent(
    """\
    {
        "reportUnusedVariable": false
    }
    """
)

UNUSED_VARIABLE_TOML_CONFIG_PYRIGHT = dedent(
    """\
    [tool.pyright]
    reportUnusedVariable = false
    """
)

UNUSED_VARIABLE_TOML_CONFIG_BASEDPYRIGHT = dedent(
    """\
    [tool.basedpyright]
    reportUnusedVariable = false
    """
)


def run_basedpyright(
    rule_runner: PythonRuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> tuple[CheckResult, ...]:
    rule_runner.set_options(
        extra_args or (), env_inherit={"PATH", "PYENV_ROOT", "HOME"}
    )
    result = rule_runner.request(
        CheckResults,
        [BasedPyrightRequest(BasedPyrightFieldSet.create(tgt) for tgt in targets)],
    )
    return result.results


def assert_success(
    rule_runner: PythonRuleRunner,
    target: Target,
    *,
    extra_args: list[str] | None = None,
) -> None:
    result = run_basedpyright(rule_runner, [target], extra_args=extra_args)
    assert len(result) == 1
    assert result[0].exit_code == 0
    assert "0 errors, 0 warnings, 0 notes" in result[0].stdout.strip()
    assert result[0].report == EMPTY_DIGEST


@pytest.mark.platform_specific_behavior
@pytest.mark.parametrize(
    "major_minor_interpreter",
    all_major_minor_python_versions(BasedPyright.default_interpreter_constraints),
)
def test_passing(rule_runner: PythonRuleRunner, major_minor_interpreter: str) -> None:
    _ = rule_runner.write_files(
        {f"{PACKAGE}/f.py": GOOD_FILE, f"{PACKAGE}/BUILD": "python_sources()"}
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    assert_success(
        rule_runner,
        tgt,
        extra_args=[
            f"--basedpyright-interpreter-constraints=['=={major_minor_interpreter}.*']"
        ],
    )


def test_failing(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {f"{PACKAGE}/f.py": BAD_FILE, f"{PACKAGE}/BUILD": "python_sources()"}
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    result = run_basedpyright(rule_runner, [tgt])
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/f.py:4" in result[0].stdout
    assert result[0].report == EMPTY_DIGEST


def test_multiple_targets(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/good.py": GOOD_FILE,
            f"{PACKAGE}/bad.py": BAD_FILE,
            f"{PACKAGE}/needs_config.py": NEEDS_CONFIG_FILE,
            f"{PACKAGE}/BUILD": "python_sources()",
        }
    )
    tgts = [
        rule_runner.get_target(Address(PACKAGE, relative_file_path="good.py")),
        rule_runner.get_target(Address(PACKAGE, relative_file_path="bad.py")),
        rule_runner.get_target(Address(PACKAGE, relative_file_path="needs_config.py")),
    ]
    result = run_basedpyright(rule_runner, tgts)
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/good.py" not in result[0].stdout
    assert f"{PACKAGE}/bad.py:4" in result[0].stdout
    assert f"{PACKAGE}/needs_config.py:2" in result[0].stdout
    assert result[0].report == EMPTY_DIGEST


@pytest.mark.parametrize(
    "config_path,extra_args",
    (
        ["pyrightconfig.json", []],
        [
            "custom_pyrightconfig.json",
            ["--basedpyright-config=custom_pyrightconfig.json"],
        ],
    ),
)
def test_json_config_file_fails(
    rule_runner: PythonRuleRunner, config_path: str, extra_args: list[str]
) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/f.py": NEEDS_CONFIG_FILE,
            f"{PACKAGE}/BUILD": "python_sources()",
            config_path: "{}",
        }
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    result = run_basedpyright(rule_runner, [tgt], extra_args=extra_args)
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/f.py:2" in result[0].stdout


@pytest.mark.parametrize(
    "config_path,extra_args",
    (
        ["pyrightconfig.json", []],
        [
            "custom_pyrightconfig.json",
            ["--basedpyright-config=custom_pyrightconfig.json"],
        ],
    ),
)
def test_json_config_file_succeeds(
    rule_runner: PythonRuleRunner, config_path: str, extra_args: list[str]
) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/f.py": NEEDS_CONFIG_FILE,
            f"{PACKAGE}/BUILD": "python_sources()",
            config_path: UNUSED_VARIABLE_JSON_CONFIG,
        }
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    assert_success(rule_runner, tgt, extra_args=extra_args)


@pytest.mark.parametrize(
    "config_path,extra_args,config_content",
    (
        ["pyproject.toml", [], UNUSED_VARIABLE_TOML_CONFIG_PYRIGHT],
        ["pyproject.toml", [], UNUSED_VARIABLE_TOML_CONFIG_BASEDPYRIGHT],
        [
            "custom_pyproject.toml",
            ["--basedpyright-config=custom_pyproject.toml"],
            UNUSED_VARIABLE_TOML_CONFIG_PYRIGHT,
        ],
        [
            "custom_pyproject.toml",
            ["--basedpyright-config=custom_pyproject.toml"],
            UNUSED_VARIABLE_TOML_CONFIG_BASEDPYRIGHT,
        ],
    ),
)
def test_toml_file_succeeds(
    rule_runner: PythonRuleRunner,
    config_path: str,
    extra_args: list[str],
    config_content: str,
) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/f.py": NEEDS_CONFIG_FILE,
            f"{PACKAGE}/BUILD": "python_sources()",
            config_path: config_content,
        }
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    assert_success(rule_runner, tgt, extra_args=extra_args)


def test_passthrough_args(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {f"{PACKAGE}/f.py": NEEDS_CONFIG_FILE, f"{PACKAGE}/BUILD": "python_sources()"}
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    result = run_basedpyright(
        rule_runner, [tgt], extra_args=["--basedpyright-args='--stats'"]
    )
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/f.py:2" in result[0].stdout


def test_skip(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {f"{PACKAGE}/f.py": BAD_FILE, f"{PACKAGE}/BUILD": "python_sources()"}
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    result = run_basedpyright(rule_runner, [tgt], extra_args=["--basedpyright-skip"])
    assert not result


def test_thirdparty_dependency(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {
            "BUILD": (
                "python_requirement(name='more-itertools', requirements=['more-itertools==8.4.0'])"
            ),
            f"{PACKAGE}/f.py": dedent(
                """\
                from more_itertools import flatten

                assert flatten(42) == [4, 2]
                """
            ),
            f"{PACKAGE}/BUILD": "python_sources()",
        }
    )
    tgt = rule_runner.get_target(Address(PACKAGE, relative_file_path="f.py"))
    result = run_basedpyright(rule_runner, [tgt])
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/f.py:3" in result[0].stdout


def test_dependencies(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/util/__init__.py": "",
            f"{PACKAGE}/util/lib.py": dedent(
                """\
                def capitalize(v: str) -> str:
                    return v.capitalize()
                """
            ),
            f"{PACKAGE}/util/BUILD": "python_sources()",
            f"{PACKAGE}/math/__init__.py": "",
            f"{PACKAGE}/math/add.py": dedent(
                """\
                from ..util.lib import capitalize

                def add(x: int, y: int) -> str:
                    sum = x + y
                    return capitalize(sum)  # This is the wrong type.
                """
            ),
            f"{PACKAGE}/math/BUILD": "python_sources()",
        }
    )
    tgt = rule_runner.get_target(
        Address(f"{PACKAGE}/math", relative_file_path="add.py")
    )
    result = run_basedpyright(rule_runner, [tgt])
    assert len(result) == 1
    assert result[0].exit_code == 1
    assert f"{PACKAGE}/math/add.py:5" in result[0].stdout


def test_run_only_on_specified_files(rule_runner: PythonRuleRunner) -> None:
    _ = rule_runner.write_files(
        {
            f"{PACKAGE}/good.py": GOOD_FILE,
            f"{PACKAGE}/bad.py": BAD_FILE,
            f"{PACKAGE}/BUILD": dedent(
                """\
                python_sources(name='good', sources=['good.py'], dependencies=[':bad'])
                python_sources(name='bad', sources=['bad.py'])
                """
            ),
        }
    )
    tgt = rule_runner.get_target(
        Address(PACKAGE, target_name="good", relative_file_path="good.py")
    )
    assert_success(rule_runner, tgt)
