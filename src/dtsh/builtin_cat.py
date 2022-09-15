# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'cat' command."""


from typing import Tuple

from dtsh.dtsh import Dtsh, DtshError, DtshVt, DtshCommand, DtshAutocomp
from dtsh.dtsh import DtshCommandUsageError
from dtsh.tui import DtNodeView, DtPropertyView


class DtshBuiltinCat(DtshCommand):
    """Concatenate and print devicetree content.

DESCRIPTION
The `cat` command will concatenate and print devicetree content at `PATH`.

Think Linux `/proc` file systems, e.g. `cat /proc/cpuinfo`.

`cat` supports the `$` character as a separator between a node's path and
a property name: `PATH := <node-path>[$<property-name>]`

Set the **--pager** option to page the command's output using the system pager.

EXAMPLES
```
/
❯ cat /soc/usbd@40027000
Node
             Path:         /soc/usbd@40027000
             Name:         usbd
             Unit address: 0x40027000
             Compatible:   nordic,nrf-usbd
             Status:       okay

Description
             Nordic nRF52 USB device controller


Depends-on
             soc
             interrupt-controller@e000e100 arm,v7m-nvic

Required-by
             There's no other node that directly depends on this
             node.

[...]
    
/
❯ cat /soc/i2c@40003000$interrupts
Property                          
             Name:     interrupts 
             Type:     array      
             Required: True       
             Default:             
             Value:    [3, 1]     
                                  
Description                       
             interrupts for device
```
"""

    def __init__(self, shell: Dtsh) -> None:
        super().__init__(
            'cat',
            'concatenate and print devicetree content',
            True
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' PATH'

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides Dtsh.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) == 0:
            raise DtshCommandUsageError(self, 'what do you want to cat?')
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

        if self._params:
            arg_path = self._dtsh.realpath(self._params[0])
        else:
            arg_path = self._dtsh.pwd

        i_prop = arg_path.rfind('$')
        if i_prop != -1:
            node = self._dtsh.path2node(arg_path[:i_prop])
            prop = node.props.get(arg_path[i_prop+1:])
            if prop is None:
                raise DtshError(f'no such property: {arg_path[i_prop+1:]}')
            view = DtPropertyView(prop)
        else:
            node = self._dtsh.path2node(arg_path)
            view = DtNodeView(node, self._dtsh)

        view.show(vt, self.with_pager)

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        # <node-path> := /<node-name>/.../<node-name>
        # <node-name> := <name>[@<unit-addr>]
        # <name> may contain alphanum, and: , . _ + -
        #
        # Property names may additionaly contain ? and #.
        #
        # AFAICT, the $ does not appear in the DT Specifications,
        # we'll is it as separator between a node's path and a property name.
        i_prop = prefix.rfind('$')

        if i_prop != -1:
            comps = DtshAutocomp.autocomplete_with_properties(prefix[:i_prop],
                                                              prefix[i_prop+1:],
                                                              self._dtsh)
            return (DtshAutocomp.MODE_DT_PROP, comps)

        return (DtshAutocomp.MODE_DT_NODE,
                DtshAutocomp.autocomplete_with_nodes(prefix, self._dtsh))
