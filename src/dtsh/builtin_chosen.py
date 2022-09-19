# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'chosen' command."""


from typing import Tuple

from rich.table import Table

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshAutocomp, DtshVt
from dtsh.dtsh import DtshError, DtshCommandUsageError
from dtsh.tui import DtshTui


class DtshBuiltinChosen(DtshCommand):
    """Print chosen system configuration.

DESCRIPTION
The `chosen` command prints the /system configuration choices/
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

/
❯ chosen zephyr,entropy -l
zephyr,entropy → /soc/random@4000d000 nordic,nrf-rng
```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'chosen',
            "print chosen configuration",
            True,
            [
                DtshCommandOption('use rich output', 'l', None, None),
            ]
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [CHOICE]'

    @property
    def with_rich_fmt(self) -> bool:
        return self.with_flag('-l')

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

        if self._params:
            arg_chosen = [self._params[0]]
        else:
            arg_chosen = list(self._dtsh.dt_chosen.keys())

        if self.with_pager:
            vt.pager_enter()
        if self.with_rich_fmt:
            grid = self._mk_grid_chosen_rich(arg_chosen)
        else:
            grid = self._mk_grid_chosen(arg_chosen)
        vt.write(grid)
        if self.with_pager:
            vt.pager_exit()

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        completions = list[str]()
        for choice in self._dtsh.dt_chosen:
            if choice.startswith(prefix) and (len(choice) > len(prefix)):
                completions.append(choice)
        return (DtshAutocomp.MODE_ANY, completions)

    def _mk_grid_chosen(self, arg_chosen: list[str]) -> Table:
        grid = DtshTui.mk_grid(3)
        for choice in arg_chosen:
            try:
                node = self._dtsh.dt_chosen[choice]
            except KeyError:
                raise DtshError(f'no such configuration choice: {arg_chosen[0]}')
            txt_choice = DtshTui.mk_txt(choice)
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt(node.path)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_choice)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            grid.add_row(txt_choice, txt_arrow, txt_path)
        return grid

    def _mk_grid_chosen_rich(self, arg_chosen: list[str]) -> Table:
        grid = DtshTui.mk_grid(4)
        for choice in arg_chosen:
            try:
                node = self._dtsh.dt_chosen[choice]
            except KeyError:
                raise DtshError(f'no such configuration choice: {arg_chosen[0]}')
            txt_choice = DtshTui.mk_txt(choice, DtshTui.style(DtshTui.STYLE_DT_ALIAS))
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt_node_path(node.path)
            txt_binding = DtshTui.mk_txt_node_binding(node, True, True)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_choice)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            grid.add_row(txt_choice, txt_arrow, txt_path, txt_binding)
        return grid
