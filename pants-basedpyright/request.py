from pants.core.goals.lint import LintTargetsRequest

from .fieldset import BasedPyrightFieldSet
from .subsystem import BasedPyright


class BasedPyrightRequest(LintTargetsRequest):
    field_set_type = BasedPyrightFieldSet
    tool_subsystem = BasedPyright
