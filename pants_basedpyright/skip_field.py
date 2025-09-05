from typing import final

from pants.backend.python.target_types import (
    PythonSourcesGeneratorTarget,
    PythonSourceTarget,
    PythonTestsGeneratorTarget,
    PythonTestTarget,
    PythonTestUtilsGeneratorTarget,
)
from pants.engine.target import BoolField


@final
class SkipBasedPyrightField(BoolField):
    alias = "skip_basedpyright"
    default = False
    help = "If true, don't run basedpyright on this target's code."


def rules():
    return [
        PythonSourcesGeneratorTarget.register_plugin_field(SkipBasedPyrightField),
        PythonSourceTarget.register_plugin_field(SkipBasedPyrightField),
        PythonTestsGeneratorTarget.register_plugin_field(SkipBasedPyrightField),
        PythonTestTarget.register_plugin_field(SkipBasedPyrightField),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipBasedPyrightField),
    ]
