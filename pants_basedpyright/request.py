from pants.core.goals.check import CheckRequest

from pants_basedpyright.fieldset import BasedPyrightFieldSet
from pants_basedpyright.subsystem import BasedPyright


class BasedPyrightRequest(CheckRequest):
    field_set_type = BasedPyrightFieldSet
    tool_name = BasedPyright.options_scope
