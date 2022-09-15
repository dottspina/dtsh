# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'chosen' command."""


from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.dtsh import DtshCommandUsageError
from dtsh.tui import DtshTui


class DtshBuiltinChosen(DtshCommand):
    """Print chosen system configuration.

DESCRIPTION
The `chosen` command prints the /system configuration/
 defined in the `/chosen` node of this devicetree.

EXAMPLES
```
/
❯ chosen
zephyr,entropy          → /soc/random@4000d000
zephyr,flash-controller → /soc/flash-controller@4001e000
zephyr,console          → /soc/uart@40002000
zephyr,shell-uart       → /soc/uart@40002000
zephyr,uart-mcumgr      → /soc/uart@40002000
zephyr,bt-mon-uart      → /soc/uart@40002000
zephyr,bt-c2h-uart      → /soc/uart@40002000
zephyr,sram             → /soc/memory@20000000
zephyr,flash            → /soc/flash-controller@4001e000/flash@0
zephyr,code-partition   → /soc/flash-controller@4001e000/flash@0/partitions/partition@c000
zephyr,ieee802154       → /soc/radio@40001000/ieee802154
```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'chosen',
            "print chosen configuration"
        )
        self._dtsh = shell

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, stdout: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            stdout.write(self.usage)
            return
        if len(self._params) > 0:
            raise DtshCommandUsageError(self, 'too many parameters')

        view = DtshTui.mk_grid(3)
        for name, node in self._dtsh.dt_chosen.items():
            txt_name = DtshTui.mk_txt(name)
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt(node.path)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_name)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            view.add_row(txt_name, txt_arrow, txt_path)
        stdout.write(view)
