# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell UI components."""


from abc import abstractmethod
from typing import ClassVar

import configparser
import os
import yaml

from devicetree.edtlib import ControllerAndData, Loader as edtlib_YamlLoader
from devicetree.edtlib import Node, Binding, Property, PropertySpec, Register

from rich import box
from rich.console import RenderableType
from rich.padding import Padding
from rich.style import Style, StyleType
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshVt, DtshError


class DtshTui:

    # DTSH theme.
    _theme: ClassVar[Theme|None] = None

    # Common UTF-8 symbols.
    #
    WCHAR_ELLIPSIS = '\u2026'
    WCHAR_COPYRIGHT = '\u00a9'
    WCHAR_HYPHEN = '\u2014'
    WCHAR_DASH = '\ufe4d'
    WCHAR_ARROW = '\u2192'
    WCHAR_BULLET = '-'

    # Base styles.
    #
    STYLE_DEFAULT = 'dtsh.default'
    STYLE_BOLD = 'bold'
    STYLE_DIM = 'dim'
    STYLE_ITALIC = 'italic'
    STYLE_UNDERLINE = 'underline'
    STYLE_STRIKE = 'strike'
    STYLE_APOLOGY = 'dtsh.apology'
    STYLE_TRUE = 'dtsh.true'
    STYLE_FALSE = 'dtsh.false'

    # Devicetree styles.
    #
    STYLE_DT_BINDING = 'dtsh.binding'
    STYLE_DT_COMPATS = 'dtsh.compats'
    STYLE_DT_LABEL = 'dtsh.label'
    STYLE_DT_LABELS = 'dtsh.labels'
    STYLE_DT_ALIAS = 'dtsh.alias'
    STYLE_DT_PROPERTY = 'dtsh.property'
    STYLE_DT_DESC = 'dtsh.desc'
    STYLE_DT_BUS = 'dtsh.bus'
    STYLE_DT_ON_BUS = 'dtsh.on_bus'
    STYLE_DT_IRQ = 'dtsh.irq'
    STYLE_DT_OKAY = 'dtsh.okay'
    STYLE_DT_NOT_OKAY = 'dtsh.not_okay'
    STYLE_DT_INCLUDE = 'dtsh.include'

    # Prompt (may be overidden by dtsh.prompt configuration)
    #
    PROMPT_WCHAR = '\u276f'
    PROMPT_COLOR = 88
    PROMPT_COLOR_ERROR = 99
    PROMPT_SPARSE = True

    @staticmethod
    def mk_ansi_prompt(has_error: bool = False) -> str:
        """Create an ANSI 255 colors compatible prompt.

        Arguments:
        has_error -- True if last command execution has failed.

        Returns a prompt compatible with ANSI 255 colors terminals.
        """
        # Using ANSI escape codes in input() breaks the GNU readline cursor.
        #
        # The hand-made prompt bellow uses the RL_PROMPT_{START,STOP}_IGNORE markers
        # to keep the readline state consistent.
        #
        # <SGR_SEC> := <CSI><n1, n2, ...>m
        # <CSI> := ESC[
        #       := \x1b[
        #
        # <START_IGNORE> := '\001'
        # <END_IGNORE> := '\002'
        #
        # See:
        # - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code
        # - https://wiki.hackzine.org/development/misc/readline-color-prompt.html
        # - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code#Colors
        #
        # We assume terminal has at least 255 colors.
        if has_error:
            sgr_color = f'38;5;{DtshTui.PROMPT_COLOR}'
        else:
            sgr_color = f'38;5;{DtshTui.PROMPT_COLOR_ERROR}'
        return f'\001\x1b[{sgr_color};1m\002{DtshTui.PROMPT_WCHAR}\001\x1b[0m\002 '

    @staticmethod
    def theme() -> Theme:
        if DtshTui._theme is None:
            DtshTui._theme = DtshTui._load_theme()
        return DtshTui._theme

    @staticmethod
    def style(name: str) -> Style:
        style = DtshTui.theme().styles.get(name)
        if not style:
            style = Style()
        return style

    @staticmethod
    def style_default() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_DEFAULT]

    @staticmethod
    def style_bold() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_BOLD]

    @staticmethod
    def style_dim() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_DIM]

    @staticmethod
    def style_italic() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_ITALIC]

    @staticmethod
    def style_underline() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_UNDERLINE]

    @staticmethod
    def style_strike() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_STRIKE]

    @staticmethod
    def style_apology() -> Style:
        return DtshTui.theme().styles[DtshTui.STYLE_APOLOGY]

    ############################################################################
    # Utils.
    ############################################################################

    @staticmethod
    def get_node_nick(node: Node) -> str:
        """Returns the node's name with the unit address part striped.
        """
        if node.unit_addr is not None:
            return node.name[0:node.name.rfind('@')]
        return node.name

    @staticmethod
    def get_text_summary(txt: str) -> str:
        lines = txt.strip().split('\n')
        str_short = lines[0]
        if len(lines) > 1:
            if str_short.endswith('.'):
                str_short = str_short[:-1]
            str_short += DtshTui.WCHAR_ELLIPSIS
        return str_short

    ############################################################################
    # Text
    ############################################################################

    @staticmethod
    def mk_txt(txt: str, style=None) -> Text:
        if not style:
            style = DtshTui.style_default()
        return Text(txt, style)

    @staticmethod
    def mk_txt_bold(txt: str) -> Text:
        return Text(txt, DtshTui.style_bold())

    @staticmethod
    def mk_txt_italic(txt: str) -> Text:
        return Text(txt, DtshTui.style_italic())

    @staticmethod
    def mk_txt_dim(txt: str) -> Text:
        return Text(txt, DtshTui.style_dim())

    @staticmethod
    def mk_txt_bool(is_true: bool,
                    true_str: str = 'Yes',
                    false_str: str = 'No',) -> Text:
        if is_true:
            val_str = true_str
            style = DtshTui.style(DtshTui.STYLE_TRUE)
        else:
            val_str = false_str
            style = DtshTui.style(DtshTui.STYLE_FALSE)
        return Text(val_str, style)

    @staticmethod
    def mk_txt_warn(msg: str) -> Text:
        return Text(msg, style='dtsh.warning')

    @staticmethod
    def mk_txt_desc(desc: str | None) -> Text:
        if not desc:
            return Text("No description available.",
                        DtshTui.style(DtshTui.STYLE_APOLOGY))
        return Text(desc.strip(), DtshTui.style(DtshTui.STYLE_DT_DESC))

    @staticmethod
    def mk_txt_desc_short(desc: str | None) -> Text:
        if not desc:
            return Text()
        desc_lines = desc.strip().split('\n')
        desc_short = desc_lines[0]
        if len(desc_lines) > 1:
            if desc_short.endswith('.'):
                desc_short = desc_short[:-1]
            desc_short += DtshTui.WCHAR_ELLIPSIS
        return Text(desc_short, DtshTui.style(DtshTui.STYLE_DT_DESC))

    @staticmethod
    def mk_txt_link(label: str,
                    url: str,
                    style: StyleType | None = None) -> Text:
        """Returns a text link.

        Arguments:
        label - the link label
        link - the link URL, e.g. https://docs.zephyrproject.org/
        style - the label's style
        """
        txt = Text(label, style=style or 'default')
        txt.stylize(Style(link=f'{url}'))
        return txt

    @staticmethod
    def txt_update_link_file(txt: Text, path: str) -> None:
        txt.stylize(Style(link=f'file:{path}'))

    @staticmethod
    def txt_dim(txt: Text) -> None:
        if isinstance(txt.style, Style):
            style = txt.style.without_color
        else:
            style = Style.parse(txt.style).without_color
        # Note: Style.combine([DtshTui.style('dim')]) would also work
        style += DtshTui.style('dim')
        txt.style = style

    @staticmethod
    def mk_txt_node_status(node: Node) -> Text:
        if node.status == 'okay':
            style = DtshTui.style(DtshTui.STYLE_DT_OKAY)
        else:
            style = DtshTui.style(DtshTui.STYLE_DT_NOT_OKAY)
        return Text(node.status, style)

    @staticmethod
    def mk_txt_node_nick(node: Node, with_status: bool = False) -> Text:
        txt = Text(DtshTui.get_node_nick(node))
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_name(node: Node, with_status: bool = False) -> Text:
        txt = Text(node.name)
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_bus_device(node: Node, with_status: bool = False) -> Text:
        txt = Text()
        if node.bus:
            txt = txt.append_text(
                DtshTui.mk_txt(node.bus, DtshTui.style(DtshTui.STYLE_DT_BUS))
            )
        if node.on_bus:
            prefix = "on "
            if len(txt.plain) > 0:
                prefix = " " + prefix
            txt = txt.append_text(DtshTui.mk_txt(prefix))
            txt = txt.append_text(
                DtshTui.mk_txt(str(node.on_bus),
                               DtshTui.style(DtshTui.STYLE_DT_ON_BUS))
            )
        if (len(txt.plain) > 0) and with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_registers(node: Node,
                              with_status: bool = False) -> RenderableType:
        if not node.regs:
            return Text()
        reg_rows = list[Text]()
        for reg in node.regs:
            txt = DtshTui.mk_txt_node_register(reg)
            if with_status and (node.status != 'okay'):
                DtshTui.txt_dim(txt)
            reg_rows.append(txt)
        if len (reg_rows) == 1:
            return reg_rows[0]
        grid = DtshTui.mk_grid(1)
        for reg_row in reg_rows:
            grid.add_row(reg_row)
        return grid

    @staticmethod
    def mk_txt_node_register(reg: Register) -> Text:
        reg_addr = hex(reg.addr) if (reg.addr is not None) else hex(0)
        reg_size = hex(reg.size) if (reg.size is not None) else None
        if reg_size is not None:
            return Text(f"<{reg_addr} {reg_size}>")
        return Text(f"<{reg_addr}>")

    @staticmethod
    def mk_txt_node_interrupts(node: Node,
                               with_status: bool = False) -> RenderableType:
        if not node.interrupts:
            return Text()
        irq_rows = list[Text]()
        for irq in node.interrupts:
            txt = DtshTui.mk_txt_node_irq(irq)
            if with_status and (node.status != 'okay'):
                DtshTui.txt_dim(txt)
            irq_rows.append(txt)
        if len(irq_rows) == 1:
            return irq_rows[0]
        grid = DtshTui.mk_grid(1)
        for irq_row in irq_rows:
            grid.add_row(irq_row)
        return grid

    @staticmethod
    def mk_txt_node_irq(ctrl_data: ControllerAndData) -> Text:
        irq = ctrl_data.data.get('irq')
        level = ctrl_data.data.get('priority')
        if (irq is not None) and (level is not None):
            if ctrl_data.name:
                txt = Text(f"{ctrl_data.name}[{irq}]",
                           DtshTui.style(DtshTui.STYLE_DT_IRQ))
            else:
                txt = Text(f"IRQ_{irq}", DtshTui.style(DtshTui.STYLE_DT_IRQ))
            txt.append_text(DtshTui.mk_txt(f"/{level}"))
        else:
            irq_data = list[Text]()
            for k, v in ctrl_data.data.items():
                irq_data.append(DtshTui.mk_txt(f"{k}:{str(v)}"))
            txt = Text(" ").join(irq_data)
        return txt

    @staticmethod
    def mk_txt_node_path(path:str) -> Text:
        """Create a rich node path.

        Arguments:
        path -- the node path

        Returns a rich text.
        """
        if path == '/':
            return Text('/', DtshTui.style('dtsh.path.anchor'))

        path_segments = path.split('/')
        # Skip path_segments[0] == ''.
        path_segments = path_segments[1:]

        txt_segments = list[Text]()
        for i, seg in enumerate(path_segments):
            if (i == 0) or (i == len(path_segments) - 1):
                txt_segments.append(
                    DtshTui.mk_txt(seg, DtshTui.style('dtsh.path.anchor'))
                )
            else:
                txt_segments.append(
                    DtshTui.mk_txt(seg, DtshTui.style('dtsh.path.segment'))
                )

        txt_sep = DtshTui.mk_txt('/', DtshTui.style('dtsh.path.segment'))
        return txt_sep.append_text(txt_sep.join(txt_segments))

    @staticmethod
    def mk_txt_node_addr(node: Node, with_status: bool = False) -> Text:
        if node.unit_addr is None:
            return Text()
        txt = Text(hex(node.unit_addr))
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_binding(node: Node,
                            with_link: bool = True,
                            with_status: bool = False) -> Text:
        if not node.matching_compat:
            return Text()
        txt = Text(node.matching_compat, DtshTui.style(DtshTui.STYLE_DT_BINDING))
        if node.binding_path and with_link:
            DtshTui.txt_update_link_file(txt, node.binding_path)
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_compats(node: Node,
                            shell: Dtsh,
                            with_link: bool = True,
                            with_status: bool = False) -> Text:
        if not node.compats:
            return Text()
        txt_bindings = list[Text]()
        for compat in node.compats:
            txt = Text(compat, DtshTui.style(DtshTui.STYLE_DT_COMPATS))
            if compat == node.matching_compat:
                txt.stylize(DtshTui.style('bold'))
            if with_link:
                binding = shell.dt_binding(compat)
                if binding and binding.path:
                    DtshTui.txt_update_link_file(txt, binding.path)
            if with_status and (node.status != 'okay'):
                DtshTui.txt_dim(txt)
            txt_bindings.append(txt)
        return Text(' ').join(txt_bindings)

    @staticmethod
    def mk_txt_node_label(node: Node, with_status: bool = False) -> Text:
        """Returns a rich Text element for the node 'label' property's value,
        or an empty Text().
        """
        if not node.label:
            return Text()
        txt = Text(node.label, DtshTui.style(DtshTui.STYLE_DT_LABEL))
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_labels(node: Node, with_status: bool = False) -> Text:
        """Returns a rich Text element with all DT labels for the node,
        in the order they appear in the DT source, or an empty Text().
        """
        if not node.labels:
            return Text()
        txt_labels = list[Text]()
        for label in node.labels:
            txt = Text(label, DtshTui.style(DtshTui.STYLE_DT_LABELS))
            if with_status and (node.status != 'okay'):
                DtshTui.txt_dim(txt)
            txt_labels.append(txt)
        txt = Text(', ', DtshTui.style(DtshTui.STYLE_DEFAULT)).join(txt_labels)
        return txt

    @staticmethod
    def mk_txt_node_all_labels(node: Node, with_status: bool = False) -> Text:
        """Returns a rich Text element with all known labels for the node,
        or an empty Text().

        See:
        - mk_txt_node_label()
        - mk_txt_node_labels()
        """
        txt = DtshTui.mk_txt_node_label(node, with_status=with_status)
        if len(txt.plain) > 0:
            txt.append_text(Text(', ', DtshTui.style(DtshTui.STYLE_DEFAULT)))
        txt.append_text(DtshTui.mk_txt_node_labels(node, with_status=with_status))
        return txt

    @staticmethod
    def mk_txt_node_aliases(node: Node, with_status: bool = False) -> Text:
        if not node.aliases:
            return Text()
        txt_aliases = list[Text]()
        for alias in node.aliases:
            txt_aliases.append(Text(alias, DtshTui.style(DtshTui.STYLE_DT_ALIAS)))
        txt = Text(' ').join(txt_aliases)
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_node_desc_short(node: Node,
                               with_link: bool = True,
                               with_status: bool = False) -> Text:
        txt = DtshTui.mk_txt_desc_short(node.description)
        if with_link and node.binding_path:
            if not node.matching_compat:
                # Nodes may have a binding without a matching compat: set
                # the link on the description
                DtshTui.txt_update_link_file(txt, node.binding_path)
        if with_status and (node.status != 'okay'):
            DtshTui.txt_dim(txt)
        return txt

    @staticmethod
    def mk_txt_binding(binding: Binding, with_link: bool = True) -> Text:
        if not binding.compatible:
            return Text()
        txt = Text(binding.compatible, DtshTui.style(DtshTui.STYLE_DT_BINDING))
        if binding.path and with_link:
            DtshTui.txt_update_link_file(txt, binding.path)
        return txt

    @staticmethod
    def mk_txt_reg_size(reg: Register) -> Text:
        if reg.size is None:
            return Text()
        return Text(str(reg.size))

    @staticmethod
    def mk_txt_reg_end_addr(reg: Register) -> Text:
        if reg.size is None:
            return Text()
        return Text(hex(reg.addr + reg.size - 1))

    @staticmethod
    def mk_txt_reg_name(reg: Register) -> Text:
        if reg.name is None:
            return Text()
        return Text(reg.name)

    @staticmethod
    def mk_txt_prop_spec_path(prop_spec: PropertySpec,
                              with_link: bool = True) -> Text:
        if not prop_spec.path:
            return Text()
        txt = Text(os.path.basename(prop_spec.path),
                   DtshTui.style(DtshTui.STYLE_DT_BINDING))
        if prop_spec.path and with_link:
            DtshTui.txt_update_link_file(txt, prop_spec.path)
        return txt

    @staticmethod
    def mk_txt_prop_desc(prop: Property) -> Text:
        if prop.spec and prop.spec.description:
            txt = DtshTui.mk_txt_desc(prop.spec.description)
        else:
            txt = Text("No description available.",
                       DtshTui.style(DtshTui.STYLE_APOLOGY))
        return txt

    @staticmethod
    def mk_txt_prop_value(prop: Property) -> Text:
        return DtshTui.mk_txt_dt_value(prop.val, prop.type)

    @staticmethod
    def mk_txt_dt_value(dt_val: object, dt_type: str) -> Text:
        if dt_type in ['phandle', 'path']:
            # prop value is the pointed Node
            return Text(dt_val.name)
        elif dt_type == 'boolean':
            return DtshTui.mk_txt_bool(dt_val)
        elif dt_type == 'phandles':
            # prop value is a list of pointed Node
            names = [node.name for node in dt_val]
            return Text(str(names))
        elif dt_type == 'phandle-array':
            # prop value is a list of ControllerAndData
            # controller is a Node
            controllers = [cad.controller.name for cad in dt_val]
            return Text(str(controllers))
        return Text(str(dt_val))

    ############################################################################
    # Autocomp hints.
    ############################################################################

    @staticmethod
    def mk_command_hints_display(model: list[DtshCommand]) -> Table:
        """Layout command completion hints.

        Arguments:
        model -- a command list to display as hints

        Returns a rich table.
        """
        tab = DtshTui.mk_grid(2)
        for cmd in model:
            tab.add_row(DtshTui.mk_txt(cmd.name), DtshTui.mk_txt_dim(cmd.desc))
        return tab

    @staticmethod
    def mk_option_hints_display(model: list[DtshCommandOption]) -> Table:
        """Layout option completion hints.

        Arguments:
        model -- an option list to display as hints

        Returns a rich table.
        """
        tab = DtshTui.mk_grid(2)
        for opt in model:
            tab.add_row(DtshTui.mk_txt(opt.usage), DtshTui.mk_txt_dim(opt.desc))
        return tab

    @staticmethod
    def mk_node_hints_display(model: list[Node]) -> Table:
        """Layout node completion hints.

        Arguments:
        model -- a node list to display as hints

        Returns a rich table.
        """
        tab = DtshTui.mk_grid(2)
        for node in model:
            if node.status == 'disabled':
                style = DtshTui.style_dim()
            else:
                style = DtshTui.style_default()
            txt_name = DtshTui.mk_txt(node.name, style)
            if node.description:
                txt_desc = DtshTui.mk_txt_dim(
                    DtshTui.get_text_summary(node.description)
                )
            else:
                txt_desc = None
            tab.add_row(txt_name, txt_desc)
        return tab

    @staticmethod
    def mk_property_hints_display(model: list[Property]) -> Table:
        """Layout property completion hints.

        Arguments:
        model -- a property list to display as hints

        Returns a rich table.
        """
        # ISSUE: edtlib would raise p.description.strip() not defined on NoneType,
        # let's rely on p.spec.
        tab = DtshTui.mk_grid(2)
        for prop in model:
            txt_desc = None
            if prop.spec and prop.spec.description:
                txt_desc = DtshTui.mk_txt_dim(
                    DtshTui.get_text_summary(prop.spec.description)
                )
            tab.add_row(DtshTui.mk_txt(prop.name), txt_desc)
        return tab

    @staticmethod
    def mk_binding_hints_display(model: list[Binding]) -> Table:
        """Layout bindings completion hints.

        Arguments:
        model -- a binding list to display as hints

        Returns a rich table.
        """
        tab = DtshTui.mk_grid(2)
        for binding in model:
            txt_compat = DtshTui.mk_txt(binding.compatible)
            if binding.description:
                txt_desc = DtshTui.mk_txt_dim(
                    DtshTui.get_text_summary(binding.description)
                )
            else:
                txt_desc = None
            tab.add_row(txt_compat, txt_desc)
        return tab


    ############################################################################
    # Layouts: DT objects
    ############################################################################

    @staticmethod
    def mk_form_node_common(node: Node, shell: Dtsh) -> Table:
        form = DtshTui.mk_form()
        form.add_row('Path:', node.path)
        form.add_row('Name:', DtshTui.get_node_nick(node))
        if node.unit_addr is not None:
            form.add_row('Unit address:', DtshTui.mk_txt_node_addr(node))
        if node.compats:
            form.add_row('Compatible:', DtshTui.mk_txt_node_compats(node, shell))
        if node.label:
            form.add_row('Label:', DtshTui.mk_txt_node_label(node))
        if node.labels:
            form.add_row('Labels:', DtshTui.mk_txt_node_labels(node))
        if node.aliases:
            form.add_row('Aliases:', DtshTui.mk_txt_node_aliases(node))
        form.add_row('Status:', DtshTui.mk_txt_node_status(node))
        return form

    @staticmethod
    def mk_grid_node_depends_on(node: Node) -> Table:
        if node.depends_on:
            grid = DtshTui.mk_grid(2)
            for node in node.depends_on:
                grid.add_row(node.name, DtshTui.mk_txt_node_binding(node))
        else:
            grid = DtshTui.mk_grid(1)
            grid.add_row(Text("This node does not directly depend on any node.",
                              DtshTui.style(DtshTui.STYLE_APOLOGY)))
        return grid

    @staticmethod
    def mk_grid_node_required_by(node: Node) -> Table:
        if node.required_by:
            grid = DtshTui.mk_grid(2)
            for node in node.required_by:
                grid.add_row(node.name, DtshTui.mk_txt_node_binding(node))
        else:
            grid = DtshTui.mk_grid(1)
            grid.add_row(Text("There's no other node that directly depends on this node.",
                              DtshTui.style(DtshTui.STYLE_APOLOGY)))
        return grid

    @staticmethod
    def mk_grid_node_registers(node: Node) -> Table:
        if node.regs:
            grid = DtshTui.mk_grid_simple_head(
                ['Address', 'Size', 'End', 'Name']
            )
            for reg in node.regs:
                grid.add_row(Text(hex(reg.addr)),
                             DtshTui.mk_txt_reg_size(reg),
                             DtshTui.mk_txt_reg_end_addr(reg),
                             DtshTui.mk_txt_reg_name(reg))
        else:
            grid = DtshTui.mk_grid(1)
            grid.add_row(Text("This node does not define any register.",
                              DtshTui.style(DtshTui.STYLE_APOLOGY)))
        return grid

    @staticmethod
    def mk_grid_node_properties(node: Node) -> Table:
        if node.props:
            grid = DtshTui.mk_grid_simple_head(['Name', 'Type', 'Value'])
            for _, prop in node.props.items():
                grid.add_row(
                    DtshTui.mk_txt(prop.name, DtshTui.style(DtshTui.STYLE_DT_PROPERTY)),
                    prop.type,
                    DtshTui.mk_txt_prop_value(prop))
        else:
            grid = DtshTui.mk_grid(1)
            grid.add_row(Text("This node does not define any property.",
                              DtshTui.style(DtshTui.STYLE_APOLOGY)))
        return grid

    @staticmethod
    def mk_form_property(prop:Property) -> Table:
        form = DtshTui.mk_form()
        form.add_row(
            'Name:',
            DtshTui.mk_txt(prop.name, DtshTui.style(DtshTui.STYLE_DT_PROPERTY))
        )
        form.add_row('Type:', prop.type)
        form.add_row('Required:', DtshTui.mk_txt_bool(prop.spec.required))
        form.add_row('Value:', DtshTui.mk_txt_prop_value(prop))
        if prop.spec.path:
            form.add_row('From:', DtshTui.mk_txt_prop_spec_path(prop.spec))
        if prop.spec.default:
            form.add_row('Default:',
                         DtshTui.mk_txt_dt_value(prop.spec.default, prop.type))
        return form

    @staticmethod
    def mk_form_prop_name_val(prop:Property) -> Table:
        form = DtshTui.mk_form()
        form.add_row('Name:', prop.name)
        form.add_row('Value:', DtshTui.mk_txt_prop_value(prop))
        return form

    @staticmethod
    def mk_form_prop_spec(prop_spec: PropertySpec) -> Table:
        form = DtshTui.mk_form()
        form.add_row(
            'Name:',
            DtshTui.mk_txt(prop_spec.name,
                           DtshTui.style(DtshTui.STYLE_DT_PROPERTY))
        )
        form.add_row('Type:', prop_spec.type)
        form.add_row('Required:', DtshTui.mk_txt_bool(prop_spec.required))
        if prop_spec.default:
            form.add_row(
                'Default:',
                DtshTui.mk_txt_dt_value(prop_spec.default, prop_spec.type)
            )
        return form

    @staticmethod
    def mk_node_tree_item(node: Node,
                          width: list[int],
                          with_status: bool = False) -> Table:
        grid = DtshTui.mk_grid(3)
        for i, w in enumerate(width):
            if w > 0:
                grid.columns[i].width = w
        grid.add_row(
            DtshTui.mk_txt_node_addr(node, with_status=with_status),
            DtshTui.mk_txt_node_nick(node, with_status=with_status),
            DtshTui.mk_txt_node_desc_short(node, with_link=False, with_status=True)
        )
        return grid

    @staticmethod
    def mk_tree_node_binding(node: Node,
                             binding: Binding,
                             shell: Dtsh) -> Tree:
        """Build the bindings tree for a node's compatible.

        Arguments:
        node -- the node the binding belongs to (used to know if the binding is
                the matched compatible for this node)
        binding -- a binding matched by this node's compatible string
        shell - the dtsh context

        Returns a tree representing the binding specifications this compatible.
        """
        anchor = DtshTui.mk_txt_binding(binding)
        if node.matching_compat == binding.compatible:
            anchor.stylize(DtshTui.style(DtshTui.STYLE_BOLD))
        tree = Tree(anchor)

        with open(binding.path, encoding="utf-8") as f:
            yaml_content = f.read()
        yaml_py = yaml.load(yaml_content, edtlib_YamlLoader)

        for inc_path in DtshTui._yaml_include_as_paths(yaml_py, shell):
            DtshTui.mk_branch_binding_path(inc_path, tree, shell)
        return tree

    @staticmethod
    def mk_branch_binding_path(path: str,
                               tree: Tree,
                               shell: Dtsh) -> None:
        with open(path, encoding="utf-8") as f:
            yaml_content = f.read()
        yaml_py = yaml.load(yaml_content, edtlib_YamlLoader)

        compat = yaml_py.get('compatible')
        if compat:
            anchor = Text(str(compat), DtshTui.style(DtshTui.STYLE_DT_COMPATS))
        else:
            anchor = Text(os.path.basename(path),
                          DtshTui.style(DtshTui.STYLE_DT_INCLUDE))
        DtshTui.txt_update_link_file(anchor, path)

        branch = tree.add(anchor)
        for inc_path in DtshTui._yaml_include_as_paths(yaml_py, shell):
            DtshTui.mk_branch_binding_path(inc_path, branch, shell)

    @staticmethod
    def _yaml_include_as_paths(yaml_py, shell: Dtsh) -> list[str]:
        # Paths for the YAML files included with "include:" statements.
        inc_paths = list[str]()
        # See edtlib.Binding._merge_includes()
        yaml_inc = yaml_py.get('include')
        if isinstance(yaml_inc, str):
            path = shell.dt_binding_path(yaml_inc)
            if path:
                inc_paths.append(path)
        elif isinstance(yaml_inc, list):
            for fname in yaml_inc:
                path = shell.dt_binding_path(fname)
                if path:
                    inc_paths.append(path)
        return inc_paths

    ############################################################################
    # Layouts: yaml
    ############################################################################

    @staticmethod
    def mk_yaml(path: str, theme: str = 'ansi_dark') -> Syntax:
        return Syntax.from_path(path, lexer='yaml', theme=theme,)

    @staticmethod
    def mk_yaml_node_binding(node: Node) -> RenderableType:
        if not node.binding_path:
            return Text("No binding source available.",
                        DtshTui.style(DtshTui.STYLE_APOLOGY))
        grid = DtshTui.mk_grid(1)
        txt_path = Text(os.path.basename(node.binding_path))
        DtshTui.txt_update_link_file(txt_path, node.binding_path)
        grid.add_row(txt_path)
        grid.add_row(None)
        grid.add_row(DtshTui.mk_yaml(node.binding_path))
        return grid

    @staticmethod
    def mk_yaml_binding(binding: Binding) -> RenderableType:
        if not (binding and binding.path):
            return Text("No binding source available.",
                        DtshTui.style(DtshTui.STYLE_APOLOGY))
        grid = DtshTui.mk_grid(1)
        txt_path = Text(os.path.basename(binding.path))
        DtshTui.txt_update_link_file(txt_path, binding.path)
        grid.add_row(txt_path)
        grid.add_row(None)
        grid.add_row(DtshTui.mk_yaml(binding.path))
        return grid

    ############################################################################
    # Layouts: base
    ############################################################################

    @staticmethod
    def mk_grid(cols: int) -> Table:
        grid = Table.grid(padding=(0, 1))
        for _ in range(0, cols):
            grid.add_column()
        return grid

    @staticmethod
    def mk_form(name_style: Style | None = None,
                value_style: Style | None = None ) -> Table:
        form = DtshTui.mk_grid(2)
        if name_style:
            form.columns[0].style = name_style
        if value_style:
            form.columns[1].style = value_style
        return form

    @staticmethod
    def form_add(form: Table, name: str, val: str):
        form.add_row(name, val)

    @staticmethod
    def mk_grid_simple_head(cols: list[str]) -> Table:
        grid = Table.grid(padding=(0, 1))
        grid.box = box.SIMPLE_HEAD
        grid.show_header = True
        grid.header_style = DtshTui.style(DtshTui.STYLE_DEFAULT)
        for header in cols:
            grid.add_column(header=header)
        return grid

    @staticmethod
    def mk_grid_statusbar() -> Table:
        bar = Table.grid(padding=(0, 1), expand=True)
        bar.add_column(justify='left', style=DtshTui.style_default(), ratio=1)
        bar.add_column(justify='center', style=DtshTui.style_default(), ratio=1)
        bar.add_column(justify='right', style=DtshTui.style_default(), ratio=1)
        return bar

    ############################################################################
    # Internals
    ############################################################################

    @staticmethod
    def _load_theme() -> Theme:
        theme = None
        theme_path = os.path.join(Dtsh.cfg_dir_path(), 'theme')
        if os.path.isfile(theme_path):
            try:
                theme = Theme.from_file(open(theme_path))
            except Exception:
                pass
        if not theme:
            theme_path = os.path.join(os.path.dirname(__file__), 'theme')
            theme = Theme.from_file(open(theme_path))
        # load custom dtsh config
        config = configparser.ConfigParser()
        config.read_file(open(theme_path))
        for name, value in config.items('dtsh'):
            if name == 'dtsh.prompt.wchar':
                DtshTui.PROMPT_WCHAR = value
            elif name == 'dtsh.bullet.wchar':
                DtshTui.WCHAR_BULLET = value
            elif name == 'dtsh.prompt.color':
                DtshTui.PROMPT_COLOR = value
            elif name == 'dtsh.prompt.color.error':
                DtshTui.PROMPT_COLOR_ERROR = value
        return theme


############################################################################
# Widget: re-usable components alternative to DtshTui.mk_xxx() API
############################################################################

class DtshTuiWidget(object):
    """A widget is a renderable factory for model or state objects.
    """

    @abstractmethod
    def as_renderable(self) -> RenderableType:
        """Returns the renderable for the model or state object this widget
        represents.
        """


class DtshTuiBulletList(DtshTuiWidget):
    """Simple bullet list.
    """

    # List layout.
    _grid: Table

    # List item prefix, default to "    - ".
    _bullet: str

    def __init__(self,
                 label: str | Text,
                 bullet: str  | None = None) -> None:
        """Initialize the widget.

        Arguments:
        label -- the list label (typically ends with ":"),
                 as a string or a rich Text
        bulet -- the bullet symbol, defaults to "-"
        """
        self._grid = Table.grid(padding=(0, 1))
        self._bullet = bullet or f"    {DtshTui.WCHAR_BULLET} "
        self._grid.add_row(label)

    def add_item(self, item: str | Text) -> None:
        """
        """
        r_item = DtshTui.mk_txt(self._bullet)
        if isinstance(item, Text):
            r_item = r_item.append_text(item)
        else:
            r_item.append(item)
        self._grid.add_row(r_item)

    def as_renderable(self) -> RenderableType:
        """Implements DtshTuiWidget.as_renderable().
        """
        return self._grid


class DtshTuiYaml(DtshTuiWidget):
    """A widget is a renderable factory for YAML files.
    """

    _grid: Table

    def __init__(self, path:str, with_title: bool = True) -> None:
        """Initialize YAML layout.
        """
        self._grid = DtshTui.mk_grid(1)
        if with_title:
            r_name = DtshTui.mk_txt_link(
                os.path.basename(path),
                f"file:{path}",
                style='dtsh.basename'
            )
            self._grid.add_row(r_name)
            self._grid.add_row()
        self._grid.add_row(DtshTui.mk_yaml(path))

    def as_renderable(self) -> RenderableType:
        """Implements DtshTuiWidget.as_renderable().
        """
        return self._grid


class DtshTuiForm(DtshTuiWidget):
    """A widget is a renderable factory for model or state objects.
    """

    # Field separator.
    FIELD_SEP: Text = Text(":", style=DtshTui.style_default())

    # 2-columns form layout.
    _form: Table

    # Style for all field labels.
    _label_style: StyleType

    # Default style for field values.
    _value_style: StyleType

    def __init__(self,
                 label_style: StyleType | None = None,
                 value_style: StyleType | None = None) -> None:
        """
        Arguments:
        label_style --
        value_style --
        """
        self._label_style = label_style or DtshTui.style_default()
        self._value_style = value_style or DtshTui.style_default()
        self._form = Table.grid(padding=(0, 1))
        self._form.add_column()
        self._form.add_column()

    def add_field(self,
                  label: str,
                  value: str | None,
                  default: str = "Unknown",
                  style: StyleType | None = None) -> None:
        """Add a string field.

        Arguments:
        label -- the field label
        value -- the field value as a rich Text
        default -- value string representing None values
        style --
        """
        r_label = Text(label, style=self._label_style)
        r_label.append_text(DtshTuiForm.FIELD_SEP)
        if value:
            r_value = Text(value, style=style or self._value_style)
        else:
            r_value = DtshTui.mk_txt_dim(default)
        self._form.add_row(r_label, r_value)

    def add_field_rich(self,
                       label: str,
                       value: Text | None,
                       default: str = "Unknown") -> None:
        """Add a rich field.

        Arguments:
        label -- the field label
        value -- the field value as a rich Text
        default -- value string representing None values
        """
        r_label = Text(label, style=self._label_style)
        r_label.append_text(DtshTuiForm.FIELD_SEP)
        r_value = value or DtshTui.mk_txt_dim(default)
        self._form.add_row(r_label, r_value)

    def as_renderable(self) -> RenderableType:
        """Implements DtshTuiWidget.as_renderable().
        """
        return self._form


############################################################################
# Flexible node table with format string support.
############################################################################

class LsNodeColumn(object):
    """Nodes table view column.
    """

    # E.g. "b"
    _spec: str

    # E.g. "Bus"
    _header: str

    def __init__(self, spec: str, header: str) -> None:
        """
        Arguments:
        spec -- the column's format specifier, e.g. "N" for the node name
        header -- the column's header, e.g. "Name"
        """
        self._spec = spec
        self._header = header

    @property
    def spec(self) -> str:
        """The column's format specifier.
        """
        return self._spec

    @property
    def header(self) -> str:
        """The column's header.
        """
        return self._header

    @abstractmethod
    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        """Returns a rich view for the colum information,
        or an empty Text() element when the node does not define
        the requested information.
        """

class LsColumnNodeName(LsNodeColumn):
    """The node name (DTSpec 2.2.1).

    Format specifier is "N".
    """

    def __init__(self) -> None:
        super().__init__("N", "Name")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_name(node, with_status=True)


class LsColumnNodeAddr(LsNodeColumn):
    """The unit-address component of the node name.

    Format specifier is "a".
    """

    def __init__(self) -> None:
        super().__init__("a", "Address")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_addr(node, with_status=True)


class LsColumnNodeNick(LsNodeColumn):
    """The node name with the unit address component striped.

    Format specifier is "n".
    """

    def __init__(self) -> None:
        super().__init__("n", "Name")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_nick(node, with_status=True)


class LsColumnNodeDesc(LsNodeColumn):
    """A summary of the desricription string from the node binding.

    Format specifier is "d".
    """

    def __init__(self) -> None:
        super().__init__("d", "Description")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_desc_short(node, with_status=True)


class LsColumnNodePath(LsNodeColumn):
    """The node path name (DT 2.2.3).

    Format specifier is "p".
    """

    def __init__(self) -> None:
        super().__init__("p", "Path")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        txt = DtshTui.mk_txt(node.path)
        if node.status != 'okay':
            DtshTui.txt_dim(txt)
        return txt


class LsColumnNodeLabel(LsNodeColumn):
    """The node label that is the value of its 'label' property.

    Format specifier is "l".
    """

    def __init__(self) -> None:
        super().__init__("l", "Label")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_label(node, with_status=True)


class LsColumnNodeLabels(LsNodeColumn):
    """All known labels for the node, apppending the DT labels
    to its 'label' property value.

    Format specifier is "L".
    """

    def __init__(self) -> None:
        """Format specifier is "L".
        """
        super().__init__("L", "Labels")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_all_labels(node, with_status=True)


class LsColumnNodeStatus(LsNodeColumn):
    """The node status that is the value of its 'status' property (DTSpec 2.3.4).

    Format specifier is "s".
    """

    def __init__(self) -> None:
        super().__init__("s", "Status")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_status(node)


class LsColumnNodeCompatible(LsNodeColumn):
    """The value of the compatible property for the node (DTSpec 2.3.1),
    should be ordered from most to lesser specific.

    Format specifier is "c".
    """

    def __init__(self) -> None:
        super().__init__("c", "Compatible")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_compats(node, shell, with_status=True)


class LsColumnNodeBinding(LsNodeColumn):
    """The compatible from the binding that matched the node.

    Format specifier is "C".
    """

    def __init__(self) -> None:
        super().__init__("C", "Binding")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_binding(node,
                                           with_link=True,
                                           with_status=True)

class LsColumnNodeAliases(LsNodeColumn):
    """The aliases for the node, fetched from /aliases.

    Format specifier is "A".
    """

    def __init__(self) -> None:
        super().__init__("A", "Aliases")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_aliases(node, with_status=True)


class LsColumnNodeBus(LsNodeColumn):
    """The bus device information for the node.

    Format specifier is "b".
    """

    def __init__(self) -> None:
        super().__init__("b", "Bus")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_bus_device(node, with_status=True)


class LsColumnNodeReg(LsNodeColumn):
    """The bus device information for the node.

    Format specifier is "r".
    """

    def __init__(self) -> None:
        super().__init__("r", "Registers")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_registers(node, with_status=True)


class LsColumnNodeInterrupts(LsNodeColumn):
    """The interrupts generated by this node.

    Format specifier is "i".
    """

    def __init__(self) -> None:
        super().__init__("i", "Interrupts")

    def mk_view(self, node: Node, shell: Dtsh) -> RenderableType:
        return DtshTui.mk_txt_node_interrupts(node, with_status=True)


class LsNodeTable(object):
    """Configurable table view for a list of nodes.

    Visible columns are configured through a format string, e.g. "naLcd".

    Defined format specifiers:

        | Specifier | Format                                    | DTSpec  |
        |-----------|-------------------------------------------|---------|
        | `N`       | The node name                             | 2.2.1   |
        | `a`       | The unit-address                          |         |
        | `n`       | The node name with the address striped    |         |
        | `d`       | The description from the node binding     |         |
        | `p`       | The node path name                        | 2.2.3   |
        | `l`       | The node 'label' property                 |         |
        | `L`       | All known labels for the node             |         |
        | `s`       | The node 'status' property                | 2.3.4   |
        | `c`       | The 'compatible' property for the node    | 2.3.1   |
        | `C`       | The node binding (aka matched compatible) |         |
        | `A`       | The node aliases                          |         |
        | `b`       | The bus device information for the node   |         |
        | `r`       | The node 'reg' property                   | 2.3.6   |
        | `i`       | The interrupts generated by the node      | 2.4.1.1 |
    """

    _dtsh: Dtsh

    # The columns for the requested format.
    _cols: list[LsNodeColumn]

    # The actual view.
    _grid: Table

    DEFAULT_FMT = "naLAcd"

    def __init__(self, shell: Dtsh, fmt: str | None = None) -> None:
        """Initialize a new node table.

        Arguments:
        shell -- the client DT shell
        fmt -- the format string, defaults to "naLAcd".

        Raises DtshError when the format specifiers string is invalid.
        """
        self._dtsh = shell
        self._cols = list[LsNodeColumn]()
        for spec in (fmt or LsNodeTable.DEFAULT_FMT):
            col = LsNodeTable._colspecs.get(spec)
            if not col:
                raise DtshError(f"unknwon format specifier {spec}")
            self._cols.append(col)
        self._grid = DtshTui.mk_grid_simple_head(
            [col.header for col in self._cols]
        )

    def add_node_row(self, node: Node) -> None:
        """Add a node to the table.
        """
        colviews = [col.mk_view(node, self._dtsh) for col in self._cols]
        self._grid.add_row(*colviews)

    def as_view(self) -> Table:
        """Returns the view for the node table.
        """
        return self._grid

    # Available columns.
    _colspecs: dict[str, LsNodeColumn] = {
        col.spec: col for col in [
            LsColumnNodeName(),
            LsColumnNodeAddr(),
            LsColumnNodeNick(),
            LsColumnNodeDesc(),
            LsColumnNodePath(),
            LsColumnNodeLabel(),
            LsColumnNodeLabels(),
            LsColumnNodeStatus(),
            LsColumnNodeCompatible(),
            LsColumnNodeBinding(),
            LsColumnNodeAliases(),
            LsColumnNodeBus(),
            LsColumnNodeReg(),
            LsColumnNodeInterrupts(),
        ]
    }


############################################################################
# Views
############################################################################

class DtshTuiView(object):
    """A view will eventually show itself on a rich VT.
    """

    @abstractmethod
    def show(self, vt: DtshVt, with_pager: bool = False) -> None:
        """Show this view on a console.

        Arguments:
        vt -- the VT to write the view to
        with_pager -- if True, the output will be paged
        """


class DtshTuiGridView(DtshTuiView):
    """Base grid layout with pager support.
    """

    # View rich table layout.
    _grid: Table

    def __init__(self, cols: int = 1, expand: bool = False) -> None:
        """Initialize the grid.

        Arguments:
        cols -- number of columns, defaults to 1
        expand -- if True, axpand the layout to fit the available horizontal
                  space, defaults to False
        """
        self._grid = Table.grid(padding=(0, 1), expand=expand)
        for _ in range(0, cols):
            self._grid.add_column()

    def show(self, vt: DtshVt, with_pager: bool = False) -> None:
        """Implements DtshTView.show().
        """
        if with_pager:
            vt.pager_enter()
        vt.write(self._grid)
        if with_pager:
            vt.pager_exit()


class DtshTuiStructuredView(DtshTuiGridView):
    """View with content divided into named sections.

    Two-columns grid: the former column holds section names,
    the later section contents.
    """

    def __init__(self) -> None:
        """Initialize the view.
        """
        super().__init__(cols=2)

    def add_section(self, name: str, content: RenderableType) -> None:
        """Add a section.

        Note that this unconditionally adds an empty row bellow the content row.

        Arguments:
        name -- the section's label
        content -- the section's content
        """
        label = Text(name, DtshTui.style('bold'))
        self._grid.add_row(label, None)
        self._grid.add_row(None, content)
        self._grid.add_row(None, None)


class DtshTuiPortraitView(DtshTuiGridView):
    """Vertical layout with indented contents.

    One column grid where different rows have different indentation levels.
    """

    def __init__(self, expand: bool = False) -> None:
        """Initialize the view.

        Arguments:
        expand -- if True, axpand the layout to fit the available horizontal
                  space, defaults to False
        """
        super().__init__(cols=1, expand=expand)

    def add(self, content: RenderableType, indent_size: int = 0) -> None:
        """Add conttent to this view.

        Arguments:
        content -- the rich content to add
        indent_size -- indentation in number of characters
        """
        self._grid.add_row(Padding(content, (0, indent_size)))


class DtshTuiMemo(DtshTuiPortraitView):
    """Portrait view organized in named entries.

    This is a more predictable layout alternative to DtshTuiStructuredView.

    Entries will show up as bellow, where dots represent the memo indentation:
    FOO
    ........FOO content begins
            content continue

    BAR
    ........BAR content begins
            content continue
    """

    def __init__(self, indent_size:int = 8, expand: bool = False) -> None:
        """Initialize the view.

        Arguments:
        indent_size -- content indentation in number of characters,
                       defaults to 8
        expand -- if True, axpand the layout to fit the available horizontal
                  space, defaults to False
        """
        super().__init__(expand=expand)
        self._indent_size = indent_size

    def add_entry(self, name: str, content: RenderableType | None) -> None:
        """Add a named entry to the memo.

        Arguments:
        name -- the entry's label (will be uppercased)
        content -- the rich content to add
        is_last -- if False, an empty row is appended bellow the content row
        """
        if self._grid.row_count > 0:
            # Add empty row after previous entry.
            self._grid.add_row(None)
        self._grid.add_row(DtshTui.mk_txt_bold(name.upper()))
        if content is None:
            content = DtshTui.mk_txt("Information not available.",
                                     style=DtshTui.style_apology())
        self._grid.add_row(Padding(content, (0, self._indent_size)))


class DtNodeView(DtshTuiStructuredView):
    """Structured view for detailed node information.
    """

    def __init__(self, node:Node, shell:Dtsh) -> None:
        """Initialize the view.

        Arguments:
        node -- the node to show
        shell -- the context shell
        """
        super().__init__()
        self.add_section('Node',
                         DtshTui.mk_form_node_common(node, shell))
        self.add_section('Description',
                         DtshTui.mk_txt_desc(node.description))
        self.add_section('Depends-on',
                         DtshTui.mk_grid_node_depends_on(node))
        self.add_section('Required-by',
                         DtshTui.mk_grid_node_required_by(node))
        self.add_section('Registers',
                         DtshTui.mk_grid_node_registers(node))
        self.add_section('Properties',
                         DtshTui.mk_grid_node_properties(node))
        self.add_section('Specified-by',
                         DtshTui.mk_yaml_node_binding(node))
        self._add_section_bindings_tree(node, shell)

    def _add_section_bindings_tree(self, node: Node, shell:Dtsh) -> None:
        grid = DtshTui.mk_grid(1)
        N = len(node.compats)
        for i, compat in enumerate(node.compats):
            binding = shell.dt_binding(compat)
            if binding:
                tree = DtshTui.mk_tree_node_binding(node, binding, shell)
                grid.add_row(tree)
                i += 1
                if i < N:
                    grid.add_row(None)
        self.add_section("Bindings", grid)


class DtPropertyView(DtshTuiStructuredView):
    """Structured view for detailed property information.

    Most of the information will show up only when the property's specification
    is available.
    """
    def __init__(self, prop:Property) -> None:
        """Initialize the view.

        Arguments:
        prop -- the property to show
        shell -- the context shell
        """
        super().__init__()
        if prop.spec:
            self.add_section('Property',
                             DtshTui.mk_form_property(prop))
            self.add_section('Description', DtshTui.mk_txt_prop_desc(prop))
            self.add_section('Binding',
                             DtshTui.mk_yaml_binding(prop.spec.binding))
        else:
            self.add_section('Property',
                             DtshTui.mk_form_prop_name_val(prop))


class DtNodeListView(DtshTuiView):
    """Node list view.

    By default, will show node contents (aka children).

    This view handles both the default and "rich output" cases.
    """

    # View rich table layout.
    _view: Table

    def __init__(self,
                 node_map: dict[str, list[Node]],
                 shell: Dtsh,
                 with_no_content: bool = False,
                 with_rich_fmt: bool = False,
                 fmt: str | None = None) -> None:
        """Initialize the view.

        Arguments:
        node_map -- maps node paths to contents (aka child nodes)
        shell -- the context shell
        with_no_content -- if True, will show nodes, not their content
        with_rich_fmt -- if True, will produce "rich output"
        """
        if with_rich_fmt:
            self._init_rich_view(node_map, shell, with_no_content, fmt)
        else:
            self._init_default_view(node_map, with_no_content)

    def show(self, vt: DtshVt, with_pager: bool = False) -> None:
        """Implements DtshTView.show().
        """
        if with_pager:
            vt.pager_enter()
        vt.write(self._view)
        if with_pager:
            vt.pager_exit()

    def _init_default_view(self,
                           node_map: dict[str, list[Node]],
                           with_no_content: bool) -> None:
        self._view = DtshTui.mk_grid(1)
        N = len(node_map)
        n = 0
        for path, nodes in node_map.items():
            if with_no_content:
                self._view.add_row(f'{path}')
            else:
                if N > 1:
                    self._view.add_row(f'{path}:')
                for node in nodes:
                    self._view.add_row(f'{node.path}')
                if n < (N - 1):
                    self._view.add_row(None)
                n += 1

    def _init_rich_view(self,
                        node_map: dict[str, list[Node]],
                        shell: Dtsh,
                        with_no_content: bool,
                        fmt: str | None) -> None:
        if with_no_content:
            ls_table = LsNodeTable(shell, fmt)
            for path, _ in node_map.items():
                node = shell.path2node(path)
                ls_table.add_node_row(node)
            self._view = ls_table.as_view()
        else:
            self._view = DtshTui.mk_grid(1)
            N = len(node_map)
            n = 0
            for path, content in node_map.items():
                self._view.add_row(Text(f"{path}:", DtshTui.style('bold')))
                if content:
                    ls_table = LsNodeTable(shell, fmt)
                    for node in content:
                        ls_table.add_node_row(node)
                    self._view.add_row(ls_table.as_view())
                if n < (N - 1):
                    self._view.add_row(None)
                n += 1


class DtNodeTreeView(DtshTuiView):
    """Node tree view.
    """

    # View rich tree layout.
    _view: Tree

    def __init__(self,
                 root: Node,
                 shell: Dtsh,
                 level: int,
                 with_rich_fmt: bool) -> None:
        """Initialize the view.

        Arguments:
        root - the tree's root node
        shell -- the context shell
        level -- the maximum tree depth; if 0, will ignore depth and stop only
                 when reaching a disabled (not okay) node
        with_rich_fmt -- if True, produce "rich output"
        """
        self._rich_fmt = with_rich_fmt
        self._dtsh = shell
        self._level = level
        self._depth = 0

        anchor = Text(root.path, DtshTui.style('bold'))
        self._view = Tree(anchor)
        self._follow_node_branch(root, self._view)

    def show(self, vt: DtshVt, with_pager: bool = False) -> None:
        """Implements DtshTView.show().
        """
        if with_pager:
            vt.pager_enter()
        vt.write(self._view)
        if with_pager:
            vt.pager_exit()

    def _follow_node_branch(self,
                            root: Node,
                            tree: Tree) -> None:
        # Increase depth when following a branch.
        self._depth += 1

        # Maximum length of child nodes nickname.
        width = self._get_branch_width(root)

        for _, node in root.children.items():
            if self._rich_fmt:
                anchor = DtshTui.mk_node_tree_item(node, width, True)
            else:
                anchor = node.name
            branch = tree.add(anchor)

            if (self._level == 0) or (self._depth < self._level):
                if node.status != 'disabled':
                    self._follow_node_branch(node, branch)

        # Decrease depth on return.
        self._depth -= 1

    def _get_branch_width(self, root: Node) -> list[int]:
        width_addr = 0
        width_nick = 0
        for _, node in root.children.items():
            nick = DtshTui.get_node_nick(node)
            w = len(nick)
            if w > width_nick:
                width_nick = w
            w = len(DtshTui.mk_txt_node_addr(node).plain)
            if w > width_addr:
                width_addr = w
        return [width_addr, width_nick]
