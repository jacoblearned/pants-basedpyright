import pytest
from pants.testutil.python_interpreter_selection import has_python_version
from pytest import Metafunc


def pytest_generate_tests(metafunc: Metafunc) -> None:
    """Parametrize test functions that use the `major_minor_interpreter` fixture.

    Tests using `major_minor_interpreter` will be run once for each major.minor Python version
    that is available on the system.
    """
    if "major_minor_interpreter" in metafunc.fixturenames:
        versions = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
        metafunc.parametrize(
            "major_minor_interpreter",
            tuple(
                pytest.param(
                    version,
                    marks=pytest.mark.skipif(
                        not has_python_version(version),
                        reason=f"Could not find python {version} on system. Skipping.",
                    ),
                )
                for version in versions
            ),
        )
