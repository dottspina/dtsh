# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Manual pages for devicetree shells."""


from abc import abstractmethod

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.padding import Padding
from rich.text import Text

from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.rich import DtshTheme


class DtshManPage(object):
    """Abstract manual page.
    """

    SECTION_DEVICETREE = 'Devicetree'
    SECTION_COMPATS = 'Compatibles'
    SECTION_DTSH = 'dtsh'

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

    def _print_section_name(self, vt: DtshVt):
        tab = DtshTheme.mk_grid(3)
        txt_name = Text(self._builtin.name, DtshTheme.STYLE_BOLD)
        txt_sep = Text(f' {DtshTheme.WCHAR_HYPHEN} ', DtshTheme.STYLE_DEFAULT)
        txt_desc = Text(self._builtin.desc, DtshTheme.STYLE_DEFAULT)
        tab.add_row(txt_name, txt_sep, txt_desc)
        self.print_section('name', tab, vt)

    def _print_section_synopsys(self, vt: DtshVt):
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

