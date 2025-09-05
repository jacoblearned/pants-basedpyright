from typing import ClassVar

from pants.core.goals.check import CheckRequest

from pants_basedpyright.fieldset import BasedPyrightFieldSet
from pants_basedpyright.subsystem import BasedPyright


class BasedPyrightRequest(CheckRequest[BasedPyrightFieldSet]):
    field_set_type: ClassVar[type] = BasedPyrightFieldSet
    tool_name: ClassVar[str] = BasedPyright.options_scope
