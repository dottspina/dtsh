# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'tree' command."""


from typing import Tuple

from dtsh.dtsh import Dtsh, DtshVt, DtshCommand, DtshCommandOption, DtshAutocomp
from dtsh.dtsh import DtshCommandUsageError

from dtsh.tui import DtNodeTreeView


class DtshBuiltinTree(DtshCommand):
    """List devicetree nodes in tree-like format.

DESCRIPTION
The `tree` command list devicetree nodes at `PATH`, which is either:

- an absolute path to a devicetree node, e.g. `/soc`
- a relative path to a devicetree node, e.g. `soc`

`PATH` supports simple path substitution:

- a leading `.` is interpreted as the current working node
- a leading `..` is interpreted as the current working node's parent

If `PATH` is unspecified, `tree` will list the current working node.

The `tree` command list nodes hierarchically as trees.

By default, `tree` will recursively walk through all not `disabled` branches: use
the **-L** option to set a maximum tree depth.

By default, `tree` will only print the nodes path: use the **-l** option to
enable a more detailed (aka *rich*) output.

Set the **--pager** option to page the command's output using the system pager.

EXAMPLES
Assuming the current working node is the devicetree's root:

1. default to `tree /`, unlimited depth:

```
/
❯ tree
/
├── chosen
├── aliases
├── soc
│   ├── interrupt-controller@e000e100
│   ├── timer@e000e010
│   ├── ficr@10000000
│   ├── uicr@10001000
│   ├── memory@20000000
│   ├── clock@40000000
│   ├── power@40000000

[...]

│   ├── acl@4001e000
│   ├── flash-controller@4001e000
│   │   └── flash@0
│   │       └── partitions
│   │           ├── partition@0
│   │           ├── partition@c000
│   │           ├── partition@73000
│   │           ├── partition@da000
│   │           └── partition@f8000

[...]

├── connector
└── analog-connector
```

2. Example of rich output with a tree depth of 2:

```
/
❯ tree -L 2 -l
/
├──  chosen
├──  aliases
├──  soc
│   ├── 0xe000e100  interrupt-controller ARMv7-M NVIC (Nested Vectored Interrupt Controller)
│   ├── 0xe000e010  timer
│   ├── 0x10000000  ficr                 Nordic FICR (Factory Information Configuration Registers)
│   ├── 0x10001000  uicr                 Nordic UICR (User Information Configuration Registers)
│   ├── 0x20000000  memory               Generic on-chip SRAM description
│   ├── 0x40000000  clock                Nordic nRF clock control node
│   ├── 0x40000000  power                Nordic nRF power control node
│   ├── 0x40001000  radio                Nordic nRF family RADIO peripheral…
│   ├── 0x40002000  uart                 Nordic nRF family UARTE (UART with EasyDMA)
│   ├── 0x40003000  i2c                  Nordic nRF family TWI (TWI master)…
│   ├── 0x40003000  spi                  Nordic nRF family SPI (SPI master)
│   ├── 0x40004000  i2c                  Nordic nRF family TWI (TWI master)…

[...]

├──  connector        GPIO pins exposed on Arduino Uno (R3) headers…
└──  analog-connector ADC channels exposed on Arduino Uno (R3) headers…
```
"""

    # Maximum display depth, 0 to follow all non disabled nodes.
    _level: int = 0

    def __init__(self, shell: Dtsh):
        super().__init__(
            'tree',
            'list devicetree nodes in tree-like format',
            True,
            [
                DtshCommandOption('use rich listing format', 'l', None, None),
                DtshCommandOption('max display depth of the tree', 'L', 'depth', 'level'),
            ]
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [PATH]'

    @property
    def with_rich_fmt(self) -> bool:
        return self.with_flag('-l')

    @property
    def arg_level(self) -> int:
        """Maximum display depth, 0 to follow all non disabled nodes.
        """
        return self._level

    def reset(self) -> None:
        """Overrides DtshCommand.reset().
        """
        super().reset()
        self._level = 0

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)

        opt = self.option('-L')
        if opt and opt.value:
            try:
                self._level = int(opt.value)
            except ValueError:
                raise DtshCommandUsageError(
                    self,
                    f"'{opt.value}' is not a valid level"
                )

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

        if self._params:
            arg_path = self._dtsh.realpath(self._params[0])
        else:
            arg_path = self._dtsh.pwd

        root = self._dtsh.path2node(arg_path)

        view = DtNodeTreeView(root,
                              self._dtsh,
                              self.arg_level,
                              self.with_rich_fmt)
        view.show(vt, self.with_pager)

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        return (DtshAutocomp.MODE_DT_NODE,
                DtshAutocomp.autocomplete_with_nodes(prefix, self._dtsh))
