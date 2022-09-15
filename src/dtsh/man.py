# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Manual pages for devicetree shells."""

import re

from abc import abstractmethod

from devicetree.edtlib import Binding

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.tui import DtshTui


class DtshManPage(object):
    """Abstract manual page.
    """

    SECTION_DTSH = 'dtsh'
    SECTION_COMPATS = 'Compatibles'

    _section: str
    _page: str
    _view: Table

    def __init__(self, section: str, page: str) -> None:
        """Create a manual page.

        Arguments:
        section -- the manual section
        page -- the manual page
        """
        self._section = section
        self._page = page
        self._view = DtshTui.mk_grid(1)
        self._view.expand = True

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
        self._add_header()
        self.add_content()
        self._add_footer()

        if not no_pager:
            vt.pager_enter()
        vt.write(self._view)
        if not no_pager:
            vt.pager_exit()

    def _add_header(self) -> None:
        """
        """
        bar = DtshTui.mk_grid_statusbar()
        bar.add_row(
            DtshTui.mk_txt_bold(self.section.upper()),
            None,
            DtshTui.mk_txt_bold(self.page.upper())
        )
        self._view.add_row(bar)
        bar.add_row(None)

    def _add_footer(self) -> None:
        """
        """
        bar = DtshTui.mk_grid_statusbar()
        bar.add_row(
            DtshTui.mk_txt_bold(Dtsh.API_VERSION),
            DtshTui.mk_txt('Shell-like interface to devicetrees'),
            DtshTui.mk_txt_bold('DTSH')
        )
        self._view.add_row(bar)

    def _add_named_content(self, name:str, content: RenderableType) -> None:
        self._view.add_row(DtshTui.mk_txt_bold(name.upper()))
        self._view.add_row(Padding(content, (0,8)))
        self._view.add_row(None)

    @abstractmethod
    def add_content(self) -> None:
        """Callback invoked by show() to setup view content.
        """


class DtshManPageBuiltin(DtshManPage):
    """
    """

    # Documented dtsh command.
    _builtin: DtshCommand

    # Regexp for page sections.
    _re: re.Pattern = re.compile('^[A-Z]+$')

    def __init__(self, builtin: DtshCommand) -> None:
        super().__init__(DtshManPage.SECTION_DTSH, builtin.name)
        self._builtin = builtin

    def add_content(self) -> None:
        self._add_content_name()
        self._add_content_synopsis()
        self._add_markdown()

    def _add_content_name(self) -> None:
        txt = DtshTui.mk_txt(self._builtin.name)
        txt.append_text(Text(f' {DtshTui.WCHAR_HYPHEN} ', DtshTui.style_default()))
        txt = DtshTui.mk_txt(self._builtin.desc)
        self._add_named_content('name', txt)

    def _add_content_synopsis(self) -> None:
        grid = DtshTui.mk_grid(1)
        grid.add_row(DtshTui.mk_txt(self._builtin.usage))
        grid.add_row(None)
        for opt in self._builtin.options:
            grid.add_row(DtshTui.mk_txt_bold(opt.usage))
            grid.add_row(DtshTui.mk_txt(f'        {opt.desc}'))
        self._add_named_content('synopsis', grid)

    def _add_markdown(self) -> None:
        content = self._builtin.__doc__
        if content:
            content = content.strip()
            content_vstr = content.splitlines()
            # Skip until 1st section
            for i, line in enumerate(content_vstr):
                if self._is_section_header(line):
                    content_vstr = content_vstr[i:]
                    break
            # Parse all sections.
            sec_name: str | None = None
            sec_vstr: list[str] | None = None
            for line  in content_vstr:
                line = line.rstrip()
                if self._is_section_header(line):
                    # Add current section's content to view if any.
                    if sec_name and sec_vstr:
                        self._add_section(sec_name, sec_vstr)
                    # Init new section's content.
                    sec_vstr = list[str]()
                    sec_name = line
                else:
                    # Append line to current section.
                    if sec_vstr is not None:
                        sec_vstr.append(line)

            if sec_name and sec_vstr:
                self._add_section(sec_name, sec_vstr)

    def _is_section_header(self, line: str) -> bool:
        return self._re.match(line) is not None

    def _add_section(self, name: str, vstr: list[str]) -> None:
        md_src = '\n'.join(vstr)
        md = Markdown(md_src)
        self._add_named_content(name, md)


class DtshManPageBinding(DtshManPage):
    """
    """

    _binding: Binding

    def __init__(self, binding: Binding) -> None:
        super().__init__(DtshManPage.SECTION_COMPATS, binding.compatible)
        self._binding = binding

    def add_content(self) -> None:
        self._add_content_compat()
        self._add_content_desc()
        self._add_content_cell_specs()
        self._add_content_bus()
        self._add_content_properties()
        self._add_content_binding()

    def _add_content_compat(self) -> None:
        grid = DtshTui.mk_form()
        grid.add_row(DtshTui.mk_txt('Compatible: '),
                     DtshTui.mk_txt_binding(self._binding))
        grid.add_row(DtshTui.mk_txt('Summary: '),
                     DtshTui.mk_txt_desc_short(self._binding.description))
        self._add_named_content('binding', grid)

    def _add_content_desc(self) -> None:
        self._add_named_content('description',
                                DtshTui.mk_txt_desc(self._binding.description))

    def _add_content_bus(self) -> None:
        if not (self._binding.bus or self._binding.on_bus):
            return

        if self._binding.bus:
            str_label = "Nodes with this compatible's binding describe bus"
            str_bus = self._binding.bus
        else:
            str_label = "Nodes with this compatible's binding appear on bus"
            str_bus = self._binding.on_bus

        txt = DtshTui.mk_txt(f'{str_label}: ')
        txt.append_text(
            DtshTui.mk_txt(str_bus, DtshTui.style(DtshTui.STYLE_DT_BUS))
        )
        self._add_named_content('bus', txt)

    def _add_content_cell_specs(self) -> None:
        # Maps specifier space names (e.g. 'gpio') to list of
        # cell names (e.g. ['pin', 'flags']).
        spec_map = self._binding.specifier2cells
        # Number of specifier spaces.
        N = len(spec_map)
        if N == 0:
            return
        grid = DtshTui.mk_grid(1)
        i_spec = 0
        for spec_space, spec_names in spec_map.items():
            grid.add_row(f'{spec_space}-cells:')
            for name in spec_names:
                grid.add_row(f'- {name}')
            if i_spec < (N - 1):
                grid.add_row(None)
            i_spec += 1
        self._add_named_content('cell specifiers', grid)

    def _add_content_properties(self) -> None:
        # Maps property names to specifications (PropertySpec).
        spec_map = self._binding.prop2specs
        # Number of property specs.
        N = len(spec_map)
        if N == 0:
            return
        grid = DtshTui.mk_grid(1)
        i_spec = 0
        for _, spec in spec_map.items():
            grid.add_row(DtshTui.mk_form_prop_spec(spec))
            if i_spec < (N - 1):
                grid.add_row(None)
            i_spec += 1
        self._add_named_content('properties', grid)

    def _add_content_binding(self) -> None:
        self._add_named_content('binding',
                                DtshTui.mk_yaml_binding(self._binding))
