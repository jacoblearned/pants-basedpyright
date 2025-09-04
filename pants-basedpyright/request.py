from pants.core.goals.check import CheckRequest

from .fieldset import BasedPyrightFieldSet
from .subsystem import BasedPyright


class BasedPyrightRequest(CheckRequest):
    field_set_type = BasedPyrightFieldSet
    tool_name = BasedPyright.options_scope
