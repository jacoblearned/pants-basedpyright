from .partition import rules as partition_rules
from .rules import rules as basedpyright_rules
from .subsystem import rules as subsystem_rules


def rules():
    return [
        *basedpyright_rules(),
        *subsystem_rules(),
        *partition_rules(),
    ]
