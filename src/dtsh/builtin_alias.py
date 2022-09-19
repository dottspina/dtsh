# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'alias' command."""


from typing import Tuple

from rich.table import Table

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshAutocomp, DtshVt
from dtsh.dtsh import DtshError, DtshCommandUsageError
from dtsh.tui import DtshTui


class DtshBuiltinAlias(DtshCommand):
    """Print defined aliases.

DESCRIPTION
The `alias` command prints the aliases defined
in the `/aliases` node of this devicetree.

EXAMPLES

```
/
❯ alias
led0            → /leds/led_0
led1            → /leds/led_1
led2            → /leds/led_2
led3            → /leds/led_3
pwm-led0        → /pwmleds/pwm_led_0
sw0             → /buttons/button_0
sw1             → /buttons/button_1
sw2             → /buttons/button_2
sw3             → /buttons/button_3
bootloader-led0 → /leds/led_0
mcuboot-button0 → /buttons/button_0
mcuboot-led0    → /leds/led_0
watchdog0       → /soc/watchdog@40010000         
spi-flash0      → /soc/qspi@40029000/mx25r6435f@0

/
❯ alias watchdog0 -l
watchdog0 → /soc/watchdog@40010000 nordic,nrf-wdt
```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'alias',
            "print defined aliases",
            True,
            [
                DtshCommandOption('use rich listing format', 'l', None, None),
            ]
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [ALIAS]'

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
            arg_aliases = [self._params[0]]
        else:
            arg_aliases = list(self._dtsh.dt_aliases.keys())

        if self.with_pager:
            vt.pager_enter()
        if self.with_rich_fmt:
            grid = self._mk_grid_aliases_rich(arg_aliases)
        else:
            grid = self._mk_grid_aliases(arg_aliases)
        vt.write(grid)
        if self.with_pager:
            vt.pager_exit()

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        completions = list[str]()
        for alias in self._dtsh.dt_aliases:
            if alias.startswith(prefix) and (len(alias) > len(prefix)):
                completions.append(alias)
        return (DtshAutocomp.MODE_ANY, completions)

    def _mk_grid_aliases(self, arg_aliases: list[str]) -> Table:
        grid = DtshTui.mk_grid(3)
        for alias in arg_aliases:
            try:
                node = self._dtsh.dt_aliases[alias]
            except KeyError:
                raise DtshError(f'no such alias: {arg_aliases[0]}')
            txt_alias = DtshTui.mk_txt(alias)
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt(node.path)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_alias)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            grid.add_row(txt_alias, txt_arrow, txt_path)
        return grid

    def _mk_grid_aliases_rich(self, arg_aliases: list[str]) -> Table:
        grid = DtshTui.mk_grid(4)
        for alias in arg_aliases:
            try:
                node = self._dtsh.dt_aliases[alias]
            except KeyError:
                raise DtshError(f'no such alias: {arg_aliases[0]}')
            txt_alias = DtshTui.mk_txt(alias, DtshTui.style(DtshTui.STYLE_DT_ALIAS))
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt_node_path(node.path)
            txt_binding = DtshTui.mk_txt_node_binding(node, True, True)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_alias)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            grid.add_row(txt_alias, txt_arrow, txt_path, txt_binding)
        return grid
