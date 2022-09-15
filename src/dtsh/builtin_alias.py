# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'pwd' command."""


from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.dtsh import DtshCommandUsageError
from dtsh.tui import DtshTui


class DtshBuiltinAlias(DtshCommand):
    """Print current working node's path.

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
```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'alias',
            "print defined aliases"
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
        for alias, node in self._dtsh.dt_aliases.items():
            txt_alias = DtshTui.mk_txt(alias)
            txt_arrow = DtshTui.mk_txt(DtshTui.WCHAR_ARROW)
            txt_path = DtshTui.mk_txt(node.path)
            if node.status != 'okay':
                DtshTui.txt_dim(txt_alias)
                DtshTui.txt_dim(txt_arrow)
                DtshTui.txt_dim(txt_path)
            view.add_row(txt_alias, txt_arrow, txt_path)
        stdout.write(view)
