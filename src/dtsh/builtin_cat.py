# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'cat' command."""


from typing import Tuple
from devicetree.edtlib import Node, Property

from rich import box
from rich.style import Style
from rich.table import Table
from rich.text import Text
from dtsh.dtsh import Dtsh, DtshError, DtshVt, DtshCommand, DtshAutocomp
from dtsh.dtsh import DtshCommandUsageError
from dtsh.rich import DtshTheme


class DtshBuiltinCat(DtshCommand):
    """Concatenate and print devicetree content.

DESCRIPTION
The `cat` command will concatenate and print devicetree content at `PATH`.

Think Linux `/proc` file systems, for e.g. `cat /proc/cpuinfo`.

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
        if len(self._params) == 0:
            raise DtshCommandUsageError(self, 'what do you want to cat?')
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return

        if self._params:
            arg_path = self._dtsh.realpath(self._params[0])
        else:
            arg_path = self._dtsh.pwd

        i_prop = arg_path.rfind('$')
        if i_prop != -1:
            view = self._mk_view_dt_prop(arg_path[:i_prop], arg_path[i_prop+1:])
        else:
            view = self._mk_view_dt_node(arg_path)

        if self.with_pager:
            vt.pager_enter()
        vt.write(view)
        if self.with_pager:
            vt.pager_exit()

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

    def _mk_view_dt_node(self, path: str) -> Table:
        node = self._dtsh.path2node(path)
        view = DtshTheme.mk_table(2)
        self._node_layout_add_node(view, node)
        self._node_layout_add_desc(view, node)
        self._node_layout_add_depends_on(view, node)
        self._node_layout_add_required_by(view, node)
        self._node_layout_add_registers(view, node)
        self._node_layout_add_properties(view, node)
        return view

    def _node_layout_add_node(self, view: Table, node: Node):
        v_node = DtshTheme.mk_grid(2)
        v_node.add_row('Path:', node.path)
        v_node.add_row('Name:', DtshTheme.get_node_nickname(node))
        if node.unit_addr is not None:
            v_node.add_row('Unit address:', hex(node.unit_addr))
        if node.compats:
            v_node.add_row('Compatible:',' '.join(node.compats))
        v_node.add_row('Status:', DtshTheme.mk_node_status(node))
        self._cat_layout_add_section(view, 'Node', v_node)

    def _node_layout_add_desc(self, view: Table, node: Node):
        if node.description:
            v_desc = Text(node.description.strip())
        else:
            v_desc = DtshTheme.mk_dim("This node does not have any description.")
        self._cat_layout_add_section(view, 'Description', v_desc)

    def _node_layout_add_depends_on(self, view: Table, node: Node):
        if node.depends_on:
            v_deps = DtshTheme.mk_grid(2)
            for dep in node.depends_on:
                if dep.matching_compat:
                    style = DtshTheme.STYLE_DEFAULT
                    if dep.binding_path:
                        style = Style(link=f'file:{dep.binding_path}')
                    txt_binding = Text(dep.matching_compat, style)
                else:
                    txt_binding = Text()
                v_deps.add_row(dep.name, txt_binding)
        else:
            v_deps = DtshTheme.mk_dim("This node does not directly depend on any node.")
        self._cat_layout_add_section(view, 'Depends-on', v_deps)

    def _node_layout_add_required_by(self, view: Table, node: Node):
        v_reqs = DtshTheme.mk_grid(2)
        if node.required_by:
            for dep in node.required_by:
                if dep.matching_compat:
                    style = DtshTheme.STYLE_DEFAULT
                    if dep.binding_path:
                        style = Style(link=f'file:{dep.binding_path}')
                    txt_binding = Text(dep.matching_compat, style)
                else:
                    txt_binding = Text()
                v_reqs.add_row(dep.name, txt_binding, style=DtshTheme.STYLE_DEFAULT)
        else:
            v_reqs = DtshTheme.mk_dim("There's no other node that directly depends on this node.")
        self._cat_layout_add_section(view, 'Required-by', v_reqs)

    def _node_layout_add_registers(self, view: Table, node: Node):
        if node.regs:
            v_regs = DtshTheme.mk_grid(3)
            for reg in node.regs:
                v_regs.add_row(Text(reg.name) if reg.name else Text(),
                               Text(hex(reg.addr)),
                               Text(str(reg.size)))
        else:
            v_regs = DtshTheme.mk_dim("This node does not define any register.")
        self._cat_layout_add_section(view, 'Registers', v_regs)

    def _node_layout_add_properties(self, view: Table, node: Node):
        if node.props:
            v_props = DtshTheme.mk_grid(3)
            v_props.box = box.SIMPLE_HEAD
            v_props.show_header = True
            v_props.header_style = DtshTheme.STYLE_DEFAULT
            v_props.columns[0].header = 'Name'
            v_props.columns[1].header = 'Type'
            v_props.columns[2].header = 'Value'
            for _, prop in node.props.items():
                v_props.add_row(prop.name, prop.type, self._prop2str(prop))
        else:
            v_props = DtshTheme.mk_dim("This node does not define any property.")
        self._cat_layout_add_section(view, 'Properties', v_props)

    def _mk_view_dt_prop(self, node_path: str, prop_name: str) -> Table:
        node = self._dtsh.path2node(node_path)
        prop = node.props.get(prop_name)
        if prop is None:
            raise DtshError(f'no such property: {prop_name}')
        if prop.spec:
            return self._mk_view_prop_spec(prop)
        else:
            return self._mk_view_prop_nospec(prop)

    def _mk_view_prop_nospec(self, prop: Property) -> Table:
        view = DtshTheme.mk_table(2)
        grid = DtshTheme.mk_grid(2)
        grid.add_row('Name:', prop.name)
        grid.add_row('Value:', self._prop2str(prop))
        self._cat_layout_add_section(view, 'Property', grid)
        return view

    def _mk_view_prop_spec(self, prop: Property) -> Table:
        view = DtshTheme.mk_table(2)
        self._prop_layout_add_prop(view, prop)
        self._prop_layout_add_desc(view, prop)
        return view

    def _prop_layout_add_prop(self, view: Table, prop: Property):
        grid = DtshTheme.mk_grid(2)
        grid.add_row('Name:', prop.name)
        grid.add_row('Type:', prop.type)
        grid.add_row('Required:', str(prop.spec.required))
        grid.add_row('Value:', self._prop2str(prop))
        if prop.spec.binding:
            grid.add_row('From:', DtshTheme.mk_binding(prop.spec.binding))
        if prop.spec.default:
            grid.add_row('Default:', prop.spec.default)
        self._cat_layout_add_section(view, 'Property', grid)

    def _prop_layout_add_desc(self, view: Table, prop: Property):
        if prop.spec.description:
            v_desc = Text(prop.spec.description.strip())
        else:
            v_desc = DtshTheme.mk_dim("This property does not have any description.")
        self._cat_layout_add_section(view, 'Description', v_desc)

    def _cat_layout_add_section(self, view: Table, label: str, section: Table|Text):
            view.add_row(DtshTheme.mk_bold(label), None)
            view.add_row(None, section)
            view.add_row(None, None)

    def _prop2str(self, prop: Property):
        if prop.type in ['phandle', 'path']:
            # prop value is the pointed Node
            return prop.val.name
        elif prop.type == 'phandles':
            # prop value is a list of pointed Node
            names = [node.name for node in prop.val]
            return str(names)
        elif prop.type == 'phandle-array':
            # prop value is a list of ControllerAndData
            controllers = [cd.controller for cd in prop.val]
            return str(controllers)
        return str(prop.val)
