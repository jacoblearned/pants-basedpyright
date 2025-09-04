from pants_basedpyright.partition import rules as partition_rules
from pants_basedpyright.rules import rules as basedpyright_rules
from pants_basedpyright.subsystem import rules as subsystem_rules


def rules():
    return [
        *basedpyright_rules(),
        *subsystem_rules(),
        *partition_rules(),
    ]
