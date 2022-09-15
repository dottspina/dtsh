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
            for line in content_vstr:
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


class DtshManPageDtsh(DtshManPage):
    """
    """

    # Regexp for page sections.
    _re: re.Pattern = re.compile('^[A-Z]+$')

    def __init__(self) -> None:
        super().__init__(DtshManPage.SECTION_DTSH, 'dtsh')

    def add_content(self) -> None:
        self._add_content_as_md()

    def _add_content_as_md(self):
        md_src = _DTSH_MAN_PAGE.strip()
        md = Markdown(md_src)
        self._view.add_row(Padding(md, (0,8)))
        self._view.add_row(None)

    def _add_content_as_sections(self):
        # Parse all sections.
        sec_name: str | None = None
        sec_vstr: list[str] | None = None
        content_vstr = _DTSH_MAN_PAGE.strip().splitlines()
        for line in content_vstr:
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


_DTSH_MAN_PAGE="""
# A devicetree shell

`dtsh` is a *shell-like* interface to a devicetree:

- a file-system metaphor mapped to devicetree path names
- common commands (for e.g. `ls`) and option (for e.g. '-l')
  syntax compatible with GNU getopt
- [GNU readline](https://tiswww.cwru.edu/php/chet/readline/rltop.html)
  integration for commands history, auto-completion support,
  and well-known key bindings
- *rich* user interface ([Python rich](https://pypi.org/project/rich))

This tool was created to explore Zephyr's
[devicetree](https://docs.zephyrproject.org/latest/build/dts/intro.html)
and
[bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html).

See also: [dtsh introductory video](https://youtu.be/pc2AMx1iPPE) (Youtube).

## SYNOPSIS

To start a shell session: `dtsh [<dts-file>] [<binding-dir>*]`

Where:

- `<dts-file>`: Path to a device tree source file (`.dts`);
  if unspecified, defaults to `$PWD/build/zephyr/zephyr.dts`
- `<binding-dirs>`: List of path to search for DT bindings (`.yaml`);
  if unspecified, and the environment variable `ZEPHYR_BASE` is set,
  defaults to Zephyr's DT bindings

To open an arbitrary DT source file, with custom bindings:

```
$ dtsh /path/to/foobar.dts /path/to/custom/bindings /path/to/other/custom/bindings
```

To open a DT source file with Zephyr's bindings (`$ZEPHYR_BASE/boards`
and `$ZEPHYR_BASE/dts/bindings`):

```
$ export ZEPHYR_BASE=/path/to/zephyr
$ dtsh /path/to/foobar.dts
```

To *fast-open* the current Zephyr project's devicetree
(`$PWD/build/zephyr/zephyr.dts`),
assuming `ZEPHYR_BASE` is set:

```
$ cd /path/to/some/zephyr/project
$ dtsh
```

## THE SHELL

The shell is a set of **built-in** commands that interface a loaded devicetree.

### Path

Most shell built-ins operate on devicetree
[**path names**](https://devicetree-specification.readthedocs.io/en/stable/devicetree-basics.html#path-names).

`dtsh` also supports paths relative to the **current working node**,
that can be changed by the `cd` built-in, and printed by `pwd`.

The wild-card `.` represents the current working node,
and `..` its parent. The devicetree root node is its own parent.

### Built-ins

- `pwd`: print current working node's path
- `alias`: print defined aliases
- `chosen`: print chosen configuration
- `cd`: change current working node
- `ls`: list devicetree nodes
- `tree`: list devicetree nodes in tree-like format
- `cat`: concatenate and print devicetree content
- `man`: open a manual page

Use `man <built-in>` to print a command's manual page,
for e.g. `man ls`.

## USER INTERFACE

On startup, a `dtsh` session will output a banner,
followed by the first prompt:

```
$ dtsh
dtsh (0.1.0a1): Shell-like interface to a devicetree
Help: man dtsh
How to exit: q, or quit, or exit, or press Ctrl-D

/
❯
```

### The prompt

The default shell prompt is ❯.
The line immediately above the prompt shows the current working node's path.

```
/
❯ pwd
/

/
❯ cd /soc/i2c@40003000/bme680@76

/soc/i2c@40003000/bme680@76
❯
```

Pressing `Ctrl-D` at the prompt will exit the `dtsh` session.

### Command line

The `dtsh` shell grammar is quite simple: `<built-in> [OPTIONS] [PARAMS]`

Where:

- <built-in>: the command's name
- `OPTIONS`: options with [GNU getopt syntax](https://www.gnu.org/software/libc/manual/html_node/Using-Getopt.html)
  for short (for e.g. `-h`) and long (for e.g. `--help`) names
- `PARAMS`: the command's parameters, typically a single path

OPTIONS and PARAMS are not positional: `ls -l /soc` is equivalent to
`ls /soc -l`.

Short option names can combine: `-lR` is equivalent to `-l -R`.

### Commands history

Commands history is provided through GNU readline integration.

At the shell prompt, press:

- up arrow (↑) to navigate the commands history backward
- down arrow (↓) to navigate the commands history forward
- `C-r` (aka `Ctrl-R`) to search history

The history is saved on exit, and loaded on startup.

### Auto-completion

Command line auto-completion is provided through GNU readline integration.

Auto-completion is triggered by first pressing the **TAB** key twice,
then once for subsequent completions of the same command line,
and may apply to:

- command names
- command options
- command parameters

### The pager

Built-ins that may produce a large output support the `--pager` option:
the command's output is then *paged* using the system pager, typically `less`:

- use up (↑) and down (↓) arrows to navigate line by line
- use page up (⇑) and down (⇓) to navigate by *page*
- press **g** go to first line
- press **G** go to last line
- press **/** to enter search mode
- press **h** for help
- press **q** to quit

### Key bindings

Useful key bindings include:

- `C-l`: clear terminal screen
- `C-a`: move cursor to beginning of command line
- `C-e`: move cursor to end of command line
- `C-k`: *kill* text from cursor to end of command line
- `M-d`: *cut* word at cursor
- `C-y`: *yank* (aka paste)
- `C-←`: move cursor one word backward
- `C-→`: move cursor one word forward
- `↑`: navigate the commands history backward
- `↓`: navigate the commands history forward
- `C-r`: search commands history
- `TAB`: trigger auto-completion

Where:

- for e.g. `C-c` means holding the **Ctrl** key and then press **c**
- for e.g. `M-d` means holding the **Alt** (*meta*) key and then press **d**

## CONFIGURATION

`dtsh` configuration includes:

- the commands history file
- the user interface theme

This configuration is located in a specific directory `DTSH_CONFIG_DIR`:

- `$XDG_CONFIG_HOME/dtsh` if `XDG_CONFIG_HOME` is set
- `$HOME/.config/dtsh` otherwise

### History

The commands history is persisted across `dtsh` sessions in the
`$DTSH_CONFIG_DIR/history` file.

This file is automatically created. Removing it clears the history.

### Theme

Colors and such are subjective, and most importantly the rendering would
eventually depend on the terminal's font and palette, the desktop theme and so on.

Most of `dtsh` user interface's styles can be customized by creating
a *theme* file `$DTSH_CONFIG_DIR/theme`:

```
# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

# Devicetree shell default theme
#
# See:
# - Styles: https://rich.readthedocs.io/en/stable/style.html#styles
# - Standard colors: https://rich.readthedocs.io/en/stable/appendix/colors.html
# - Theme: https://rich.readthedocs.io/en/stable/style.html#style-themes

[styles]

# Default style.
dtsh.default = default on default

# Node path anchor (1st and last segments).
# Color: DeepSkyBlue3
dtsh.path.anchor = #0087af
# Node path segments.
# Color: DeepSkyBlue1
dtsh.path.segment = #00afff

# Apply to a node's (unique) matching compatible (aka binding).
# Typically: node.matching_compat is defined,
# and node.binding_path might point to the corresponding yaml file.
#
dtsh.binding = light_sea_green

# Apply to compatible strings as in node.compats.
#
dtsh.compats = light_sea_green

# Apply to descriptions from DT bindings (nodes or properties).
#
dtsh.desc = medium_orchid3

# Apply to a node's label properties.
# color: deep_sky_blue1
#
dtsh.labels = #00afff italic

# Apply to a node's labels.
# color: deep_sky_blue1
#
dtsh.label = #00afff

# Apply to descriptions bus (DT bindings)
#
dtsh.bus = dark_khaki bold

# Apply to a node's aliases.
#
dtsh.alias = turquoise2

# Apply to a property names.
#
dtsh.property = dark_sea_green

# Apply to node status 'okay'.
# Green example: spring_green3
#
dtsh.okay = default

# Apply to node status not 'okay'.
#
dtsh.not_okay = dim

# Apply when the required data to show,
# for e.g. a structured view section,
# is not available
dtsh.apology = dim italic

# Apply to boolean values.
#
dtsh.true = default
dtsh.false = dim


[dtsh]

# Prompt colors.
# See https://en.wikipedia.org/w/index.php?title=ANSI_escape_code#Colors
#
dtsh.prompt.color = 88
dtsh.prompt.color.error = 99
dtsh.prompt.wchar = ❯
```

## REFERENCES

**dtsh**

- [Home page](https://github.com/dottspina/dtsh) (GitHub)
- [Introductory video](https://youtu.be/pc2AMx1iPPE) (Youtube)

**Devicetree specifications**:

- [browse](https://devicetree-specification.readthedocs.io/en/stable/) latest stable
- [download](https://www.devicetree.org/specifications/) specifications

**Zephyr**:

- [Introduction to devicetree](https://docs.zephyrproject.org/latest/build/dts/intro.html)
- [Bindings index](https://docs.zephyrproject.org/latest/build/dts/api/bindings.html)

**Linux**:

- [Linux and the Devicetree](https://www.kernel.org/doc/html/latest/devicetree/usage-model.html)
- [Device Tree Usage](https://elinux.org/Device_Tree_Usage)
- [Device Tree Reference](https://elinux.org/Device_Tree_Reference)

"""
