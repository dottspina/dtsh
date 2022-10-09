# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'ls' command."""


from typing import Tuple
from devicetree.edtlib import Node

from dtsh.dtsh import DtshCommand, DtshCommandOption, Dtsh, DtshAutocomp, DtshVt
from dtsh.dtsh import DtshCommandUsageError
from dtsh.tui import DtNodeListView


class DtshBuiltinLs(DtshCommand):
    """List devicetree nodes.

DESCRIPTION
The `ls` command will list devicetree nodes at `PATH`, which is either:

- an absolute path to a devicetree node, e.g. `/soc`
- a relative path to a devicetree node, e.g. `soc`
- a glob pattern filtering devicetree nodes, e.g. `soc/uart*`

`PATH` supports simple path substitution:

- a leading `.` is interpreted as the current working node
- a leading `..` is interpreted as the current working node's parent

If `PATH` is unspecified, `ls` will list the current working node.

By default, `ls` will enumerate the immediate children of the devicetree node(s)
at `PATH`: use the **-R** option to enumerate the children recursively,
the **-d** option to list the node itself without its children.

By default, `ls` will only print the nodes path: use the **-l** option to
enable a more detailed (aka *rich*) output.

By default, nodes should be sorted by ascending unit address: use the **-r**
option to reverse the sort order.

Set the **--pager** option to page the command's output using the system pager.

EXAMPLES
Assuming the current working node is the devicetree's root:

1. default to `ls /`:

```
/
❯ ls
/chosen
/aliases
/soc
/pin-controller
/entropy_bt_hci
/cpus
/sw-pwm
/leds
/pwmleds
/buttons
/connector
/analog-connector
```

2. same with rich output:

```
❯ ls -l
/:
Name              Addr  Labels          Alias  Compatible                                                    Description
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
chosen
aliases
soc                                            nordic,nRF52840-QIAA nordic,nRF52840 nordic,nRF52 simple-bus
pin-controller          pinctrl                nordic,nrf-pinctrl                                            The nRF pin controller is a singleton node responsible for controlling…
entropy_bt_hci          rng_hci                zephyr,bt-hci-entropy                                         Bluetooth module that uses Zephyr's Bluetooth Host Controller Interface as…
cpus
sw-pwm                  sw_pwm                 nordic,nrf-sw-pwm                                             nRFx S/W PWM
leds                                           gpio-leds                                                     This allows you to define a group of LEDs. Each LED in the group is…
pwmleds                                        pwm-leds                                                      PWM LEDs parent node
buttons                                        gpio-keys                                                     GPIO KEYS parent node
connector               arduino_header         arduino-header-r3                                             GPIO pins exposed on Arduino Uno (R3) headers…
analog-connector        arduino_adc            arduino,uno-adc                                               ADC channels exposed on Arduino Uno (R3) headers…
```

Globing:

1. *for all* wild-card:

```
/
❯ ls *
/chosen:

/aliases:

/soc:
/soc/interrupt-controller@e000e100
/soc/timer@e000e010
/soc/ficr@10000000
/soc/uicr@10001000
/soc/memory@20000000
/soc/clock@40000000
/soc/power@40000000
/soc/radio@40001000
/soc/uart@40002000
/soc/i2c@40003000
/soc/spi@40003000

[...]

/buttons:
/buttons/button_0
/buttons/button_1
/buttons/button_2
/buttons/button_3

/connector:

/analog-connector:
```

2. filter wild-card:

```
/
❯ ls /soc/gpio* -ld
Name    Address     Labels  Aliases  Compatible         Description
────────────────────────────────────────────────────────────────────────
gpiote  0x40006000  gpiote           nordic,nrf-gpiote  NRF5 GPIOTE node
gpio    0x50000000  gpio0            nordic,nrf-gpio    NRF5 GPIO node
gpio    0x50000300  gpio1            nordic,nrf-gpio    NRF5 GPIO node
```
"""
    def __init__(self, shell: Dtsh) -> None:
        super().__init__(
            'ls',
            'list devicetree nodes',
            True,
            [
                DtshCommandOption('list node itself, not its content', 'd', None, None),
                DtshCommandOption('use rich listing format', 'l', None, None),
                DtshCommandOption('reverse order while sorting', 'r', None, None),
                DtshCommandOption('list node contents recursively', 'R', None, None),
            ]
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [PATH]'

    @property
    def with_no_content(self) -> bool:
        return self.with_flag('-d')

    @property
    def with_recursive(self) -> bool:
        return self.with_flag('-R')

    @property
    def with_reverse(self) -> bool:
        return self.with_flag('-r')

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
            arg_path = self._dtsh.realpath(self._params[0])
        else:
            arg_path = self._dtsh.pwd

        if arg_path.endswith('*'):
            # Globing.
            roots = self._dtsh.ls(arg_path)
        else:
            roots = [
                self._dtsh.path2node(arg_path)
            ]

        if self.with_reverse:
            roots.reverse()

        node_map = dict[str, list[Node]]()
        for root in roots:
            if self.with_no_content:
                node_map[root.path] = []
            else:
                if self.with_recursive:
                    self._follow_node_content(root, node_map)
                else:
                    node_map[root.path] = self._dtsh.ls(root.path)

        if self.with_reverse:
            for _, contents in node_map.items():
                contents.reverse()

        view = DtNodeListView(node_map,
                              self._dtsh,
                              self.with_no_content,
                              self.with_rich_fmt)
        view.show(vt, self.with_pager)

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        return (DtshAutocomp.MODE_DT_NODE,
                DtshAutocomp.autocomplete_with_nodes(prefix, self._dtsh))

    def _follow_node_content(self,
                             parent: Node,
                             node_map: dict[str, list[Node]]) -> None:
        node_map[parent.path] = list[Node]()
        for _, node in parent.children.items():
            node_map[parent.path].append(node)
            self._follow_node_content(node, node_map)
