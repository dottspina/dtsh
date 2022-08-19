# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Manual pages for devicetree shells."""

import os
from abc import abstractmethod

from devicetree.edtlib import Binding

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.markup import escape
from rich.padding import Padding
from rich.text import Text

from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.rich import DtshTheme


class DtshManPage(object):
    """Abstract manual page.
    """

    SECTION_DTSH = 'dtsh'
    SECTION_COMPATS = 'Compatibles'

    _section: str
    _page: str

    def __init__(self, section: str, page: str) -> None:
        """Create a manual page.

        Arguments:
        section -- the manual section
        page -- the manual page
        """
        self._section = section
        self._page = page

    @property
    def section(self) -> str:
        """The manual page's section.
        """
        return self._section

    @property
    def page(self) -> str:
        """The manual page.
        """
        return self._page

    def show(self, vt: DtshVt, no_pager: bool = False) -> None:
        """Show this man page.

        Arguments:
        vt -- the VT to show the man page on
        no_pager -- print the man page without pager
        """
        if not no_pager:
            vt.pager_enter()
        self.print_header(vt)
        self.print_body(vt)
        self.print_footer(vt)
        if not no_pager:
            vt.pager_exit()

    def print_header(self, vt: DtshVt) -> None:
        """Print man page header.
        """
        tab = DtshTheme.mk_wide_table()
        txt_sec = DtshTheme.mk_bold(self.section)
        txt_page = DtshTheme.mk_bold(self.page)
        tab.add_row(txt_sec, None, txt_page)
        vt.write(tab)
        vt.write()

    def print_footer(self, vt: DtshVt) -> None:
        """Print man page footer.
        """
        tab = DtshTheme.mk_wide_table()
        txt_version = DtshTheme.mk_bold(Dtsh.API_VERSION)
        txt_center = DtshTheme.mk_txt('Shell-like interface to devicetrees')
        txt_dtsh = DtshTheme.mk_bold('dtsh')
        tab.add_row(txt_version, txt_center, txt_dtsh)
        vt.write(tab)

    def print_section(self, name: str, content: RenderableType, vt: DtshVt):
        """Print a man page section."""
        vt.write(Text(name.upper(), DtshTheme.STYLE_BOLD))
        vt.write(Padding.indent(content, 8))
        vt.write()

    @abstractmethod
    def print_body(self, vt: DtshVt) -> None:
        """Print the manual page body.

        Actual implementation depends on the manual page's kind.
        """


class DtshBuiltinManPage(DtshManPage):
    """Manual page for shell built-in commands.
    """

    _builtin: DtshCommand

    def __init__(self, builtin: DtshCommand) -> None:
        """Create a command's manual page.

        Arguments:
        builtin -- the shell command
        """
        super().__init__(DtshManPage.SECTION_DTSH.upper(), builtin.name.upper())
        self._builtin = builtin

    def print_body(self, vt: DtshVt) -> None:
        """Overrides DtshManPage.print_body().
        """
        self._print_section_name(vt)
        self._print_section_synopsys(vt)

        docstr = self._builtin.__doc__
        if docstr:
            doc_vstr = docstr.splitlines()
            offset = self._print_section_description(doc_vstr, vt)
            if offset != -1:
                self._print_section_examples(doc_vstr, offset, vt)

    def _print_section_name(self, vt: DtshVt) -> None:
        tab = DtshTheme.mk_grid(3)
        txt_name = Text(self._builtin.name, DtshTheme.STYLE_BOLD)
        txt_sep = Text(f' {DtshTheme.WCHAR_HYPHEN} ', DtshTheme.STYLE_DEFAULT)
        txt_desc = Text(self._builtin.desc, DtshTheme.STYLE_DEFAULT)
        tab.add_row(txt_name, txt_sep, txt_desc)
        self.print_section('name', tab, vt)

    def _print_section_synopsys(self, vt: DtshVt) -> None:
        tab = DtshTheme.mk_grid(1)
        tab.add_row(Text(self._builtin.usage))
        tab.add_row(None)
        for opt in self._builtin.options:
            tab.add_row(Text(opt.usage, DtshTheme.STYLE_BOLD))
            tab.add_row(Text(f'        {opt.desc}', DtshTheme.STYLE_DEFAULT))
        self.print_section('synopsys', tab, vt)

    def _print_section_description(self, doc_vstr: list[str], vt: DtshVt) -> int:
        sz_src = len(doc_vstr)
        offset = 0
        while (offset < sz_src) and (doc_vstr[offset] != 'DESCRIPTION'):
            offset += 1
        if offset == sz_src:
            return -1

        # Stop at EXAMPLES.
        stop_at = offset
        while (stop_at < sz_src) and (doc_vstr[stop_at] != 'EXAMPLES'):
            stop_at += 1

        if stop_at > offset:
            section_vstr = doc_vstr[offset + 1:stop_at]
            md_src = '\n'.join(section_vstr)
            md = Markdown(md_src)
            self.print_section('description', md, vt)

        return stop_at

    def _print_section_examples(self,
                                doc_vstr: list[str],
                                start_at: int,
                                vt: DtshVt) -> int:
        sz_src = len(doc_vstr)
        offset = start_at
        while (offset < sz_src) and (doc_vstr[offset] != 'EXAMPLES'):
            offset += 1
        if offset == sz_src:
            return -1

        # Stop at SEEALSO.
        stop_at = offset
        while (stop_at < sz_src) and (doc_vstr[stop_at] != 'SEEALSO'):
            stop_at += 1

        if stop_at > offset:
            section_vstr = doc_vstr[offset + 1:stop_at]
            md_src = '\n'.join(section_vstr)
            md = Markdown(md_src)
            self.print_section('examples', md, vt)

        return stop_at


class DtshCompatibleManPage(DtshManPage):
    """Manual page for a compatible (aka bindings).
    """

    _binding: Binding

    def __init__(self, binding: Binding) -> None:
        """Create a command's manual page.

        Arguments:
        builtin -- the shell command
        """
        super().__init__(DtshManPage.SECTION_COMPATS.upper(),
                         binding.compatible)
        self._binding = binding

    def print_body(self, vt: DtshVt) -> None:
        """Overrides DtshManPage.print_body().
        """
        self._print_section_binding(vt)
        self._print_section_description(vt)
        self._print_section_bus(vt)
        self._print_section_cell_specs(vt)
        self._print_section_properties(vt)
        self._print_section_source(vt)

    def _print_section_description(self, vt: DtshVt) -> None:
        if self._binding.description:
            txt_desc = Text(self._binding.description.strip(),
                            DtshTheme.STYLE_BINDING_DESC)
            self.print_section('description', txt_desc, vt)

    def _print_section_binding(self, vt: DtshVt) -> None:
        tab = DtshTheme.mk_grid(2)
        tab.add_row(DtshTheme.mk_txt('Compatible:'),
                    Text(self._binding.compatible, DtshTheme.STYLE_NODE_COMPAT))

        if self._binding.description:
            str_summary = DtshTheme.get_str_summary(self._binding.description)
            tab.add_row(DtshTheme.mk_txt('Summary:'),
                        Text(str_summary, DtshTheme.STYLE_NODE_DESC))

        if self._binding.path:
            filename = os.path.basename(self._binding.path)
            str_binding_path = f'[link file:{escape(self._binding.path)}]{filename}'
        else:
            str_binding_path = DtshTheme.WCHAR_ELLIPSIS
        tab.add_row(DtshTheme.mk_txt('Specified by:'), str_binding_path)

        self.print_section('binding', tab, vt)

    def _print_section_bus(self, vt: DtshVt) -> None:
        if (self._binding.bus is None) and (self._binding.on_bus is None):
            return

        if self._binding.bus is not None:
            str_label = "Nodes with this binding's compatible describe bus"
            str_bus = self._binding.bus
        else:
            str_label = "Nodes with this binding's compatible appear on bus"
            str_bus = self._binding.on_bus

        txt_label = DtshTheme.mk_txt(f'{str_label}:')
        txt_bus = Text(str_bus, DtshTheme.STYLE_BUS)
        tab = DtshTheme.mk_grid(2)
        tab.add_row(txt_label, txt_bus)

        self.print_section('bus', tab, vt)

    def _print_section_cell_specs(self, vt: DtshVt) -> None:
        # Maps specifier space names (e.g. 'gpio') to list of
        # cell names (e.g. ['pin', 'flags'])
        spec_map = self._binding.specifier2cells
        N = len(spec_map)
        if N == 0:
            return

        tab = DtshTheme.mk_grid(1)
        i_spec = 0
        for spec_space, spec_names in spec_map.items():
            tab.add_row(f'{spec_space}-cells:')
            for name in spec_names:
                tab.add_row(f'- {name}')
            if i_spec < (N - 1):
                tab.add_row(None)
            i_spec += 1
        self.print_section('cell specifiers', tab, vt)

    def _print_section_properties(self, vt: DtshVt) -> None:
        # Maps property names to specifications (PropertySpec)
        prop_map = self._binding.prop2specs
        N = len(prop_map)
        if N == 0:
            return

        tab = DtshTheme.mk_table(1)
        for _, spec in prop_map.items():
            tab_spec = DtshTheme.mk_property_spec(spec)
            tab.add_row(tab_spec)
        self.print_section('properties', tab, vt)

    def _print_section_source(self, vt: DtshVt) -> None:
        if self._binding.path:
            view = DtshTheme.mk_yaml_view(self._binding.path)
            self.print_section('source', view, vt)

