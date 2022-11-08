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
            DtshTui.mk_txt('Shell-like interface with devicetrees'),
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
# dtsh

[Home](https://github.com/dottspina/dtsh)  [PyPI](https://pypi.org/project/devicetree/)  [Known issues](https://github.com/dottspina/dtsh/issues)

**dtsh** is an interactive *shell-like* interface with a devicetree and its bindings:

-   browse the devicetree through a familiar hierarchical file-system metaphor
-   retrieve nodes and bindings with accustomed command names and command line syntax
-   generate simple documentation artifacts by redirecting commands output to files (text, HTML, SVG)
-   common command line interface paradigms (auto-completion, history) and keybindings

## SYNOPSIS

To start a shell session: `dtsh [<dts-file>] [<binding-dir>*]`

where:

-   `<dts-file>`: path to the device tree source file in  [DTS Format](https://devicetree-specification.readthedocs.io/en/latest/chapter6-source-language.html) (`.dts`);
    if unspecified, defaults to `$PWD/build/zephyr/zephyr.dts`
-   `<binding-dir>`: directory to search for  [YAML](https://yaml.org/) binding files;
    if unspecified, and the environment variable `ZEPHYR_BASE` is set,
    defaults to [Zephyr&rsquo;s bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html#where-bindings-are-located)

ℹ See [Incomplete Zephyr bindings search path #1](https://github.com/dottspina/dtsh/issues/1)
for details and limitations.

To open an arbitrary DTS file with custom bindings:

    $ dtsh /path/to/foobar.dts /path/to/custom/bindings /path/to/other/custom/bindings

To open the same DTS file with Zephyr&rsquo;s bindings:

    $ export ZEPHYR_BASE=/path/to/zephyr
    $ dtsh /path/to/foobar.dts

## THE SHELL

`dtsh` defines a set of *built-in* commands that interface with a devicetree
and its bindings through a hierarchical file-system metaphor.

### File system metaphor

Within a `dtsh` session, a devicetree shows itself as a familiar hierarchical file-system,
where [path names](https://devicetree-specification.readthedocs.io/en/stable/devicetree-basics.html#path-names)
*look like* paths to files or directories, depending on the acting shell command.

A current *working node* is defined, similar to any shell&rsquo;s current working directory,
allowing `dtsh` to also support relative paths.

A leading `.` represents the current working node, and `..` its parent.
The devicetree root node is its own parent.

To designate properties, `dtsh` uses `$` as a separator between DT path names and [property names](https://devicetree-specification.readthedocs.io/en/stable/devicetree-basics.html#property-names)
(should be safe since `$` is an invalid character for both node and property names).

Some commands support filtering or *globbing* with trailing wild-cards `*`.

### Command strings

The `dtsh` command string is based on the
[GNU getopt](https://www.gnu.org/software/libc/manual/html_node/Using-Getopt.html) syntax.

#### Synopsis

All built-ins share the same synopsis:

    CMD [OPTIONS] [PARAMS]

where:

-   `CMD`: the built-in name, e.g. `ls`
-   `OPTIONS`: the options the command is invoked with (see bellow), e.g. `-l`
-   `PARAMS`: the parameters the command is invoked for, e.g. a path name

`OPTIONS` and `PARAMS` are not positional: `ls -l /soc` is equivalent to `ls /soc -l`.

#### Options

An option may support:

-   a short name, starting with a single `-` (e.g. `-h`)
-   a long name, starting with `--` (e.g. `--help`)

Short option names can combine: `-lR` is equivalent to `-l -R`.

An Option may also require an argument, e.g. `find /soc --interrupt 12`.

Options semantic should be consistent across commands, e.g. `-l` always means *long format*.

We also try to re-use *well-known* option names, e.g. `-r` for *reverse sort* or `-R` for *recursive*.


ℹ Trigger `TAB` completion after a single `-` to *pull* a summary
of a command's options, e.g:

```
❯ find -[TAB][TAB]
-c                    print nodes count
-q                    quiet, only print nodes count
-l                    use rich listing format
-f <fmt>              visible columns format string
-h --help             print usage summary
--name <pattern>      find by name
--compat <pattern>    find by compatible
--bus <pattern>       find by bus device
--interrupt <pattern> find by interrupt
--enabled-only        search only enabled nodes
--pager               page command output
❯ find -
```

### Built-ins

    | Built-in   |                                           |
    |------------+-------------------------------------------|
    | alias      | print defined aliases                     |
    | chosen     | print chosen configuration                |
    | pwd        | print current working node's path         |
    | cd         | change current working node               |
    | ls         | list devicetree nodes                     |
    | tree       | list devicetree nodes in tree-like format |
    | cat        | concatenate and print devicetree content  |
    | find       | find devicetree nodes                     |
    | uname      | print system information                  |
    | man        | open a manual page                        |

Use `man <built-in>` to print a command's manual page,
e.g. `man ls`.

### Manual pages

As expected, the `man` command will open the manual page for the shell itself (`man dtsh`),
or one of its built-ins (e.g. `man ls`).

Additionally, `man` can also open a manual page for a
[compatible](https://devicetree-specification.readthedocs.io/en/latest/chapter2-devicetree-basics.html#compatible),
which is essentially a view of its (YAML) bindings: e.g.  `man --compat nordic,nrf-radio`

`man` should eventually also serve as an entry point to external useful or normative documents,
e.g. the Devicetree Specifications or the Zephyr project&rsquo;s documentation.

### System information

**dtsh** may also expose *system* information, including:

- the Zephyr kernel version, e.g. `zephyr-3.1.0`, with a link to the corresponding
  release notes when available
- board information, based on the content of its YAML binding file,
  with a link to the corresponding documentation when the board
  is [supported by Zephyr](https://docs.zephyrproject.org/latest/boards/index.html)
- the configured *toolchain*, either Zephyr SDK or GNU Arm Embedded

For example:

    BOARD
        Board directory: $ZEPHYR_BASE/boards/arm/nrf52840dk_nrf52840
        Name:            nRF52840-DK-NRF52840 (Supported Boards)
        Board:           nrf52840dk_nrf52840 (DTS)

        nrf52840dk_nrf52840.yaml

        identifier: nrf52840dk_nrf52840
        name: nRF52840-DK-NRF52840
        type: mcu
        arch: arm
        ram: 256
        flash: 1024
        toolchain:
          - zephyr
          - gnuarmemb
          - xtools
        supported:
          - adc
          - arduino_gpio
          - arduino_i2c
          - arduino_spi
          - ble
          - counter
          - gpio
          - i2c
          - i2s
          - ieee802154
          - pwm
          - spi
          - usb_cdc
          - usb_device
          - watchdog
          - netif:openthread

Retrieving this information may involve environment variables (e.g. `ZEPHYR_BASE`
or `ZEPHYR_TOOLCHAIN_VARIANT`), CMake cached variables, `git` or GCC.

Refer to `man uname` for details.

### Find nodes

The `find` command permits to search the devicetree by:

- node names
- compatible strings
- bus devices
- interrupt names or numbers

For example, the command line bellow would list all enabled bus devices
that generate IRQs :


    ❯ find --enabled-only --bus * --interrupt *

`find` is quite versatile and supports a handful of options.
Refer to its extensive manual page (`man find`).

## USER INTERFACE

The `dtsh` command line interface paradigms and keybindings should sound familiar.

### The prompt

The default shell prompt is ❯.
The line immediately above the prompt shows the current working node&rsquo;s path.

    /
    ❯ pwd
    /

    /
    ❯ cd /soc/i2c@40003000/bme680@76

    /soc/i2c@40003000/bme680@76
    ❯ pwd
    /soc/i2c@40003000/bme680@76

Pressing `C-d` (aka `CTRL-D`) at the prompt will exit the `dtsh` session.

### Commands history

Commands history is provided through GNU readline integration.

At the shell prompt, press:

- up arrow (↑) to navigate the commands history backward
- down arrow (↓) to navigate the commands history forward
- `C-r` (aka `CTRL-R`) to search the commands history

The history file (typically `$HOME/.config/dtsh/history`) is saved on exit, and loaded on startup.

### Auto-completion

Command line auto-completion is provided through GNU readline integration.

Auto-completion is triggered by first pressing the `TAB` key twice,
then once for subsequent completions of the same command line, and may apply to:

- command names (aka built-ins)
- command options
- command parameters

### The pager

Built-ins that may produce large outputs support the `--pager` option: the command&rsquo;s
output is then *paged* using the system pager, typically `less`:

-   use up (↑) and down (↓) arrows to navigate line by line
-   use page up (⇑) and down (⇓) to navigate *window* by *window*
-   press `g` go to first line
-   press `G` go to last line
-   press `/` to enter search mode
-   press `h` for help
-   press `q` to quit the pager and return to the `dtsh` prompt

On the contrary, the `man` command uses the pager by default
and defines a `--no-pager` option to disable it.

### External links

`dtsh` commands output may contain links to external documents such as:

-   the local YAML binding files, that should open in the system&rsquo;s
    default text editor
-   the Devicetree specifications or the Zephyr project&rsquo;s documentation,
    that should open in the system&rsquo;s default web browser

How these links will appear in the console, and whether they are *actionable* or not,
eventually depend on the terminal and the desktop environment.

This is an example of such links: [Device Tree What It Is](https://elinux.org/Device_Tree_What_It_Is)

ℹ In particular, the environment may assume DTS files are DTS audio streams
(e.g. the VLC media player could have registered itself for handling the `.dts` file extension).
In this case, the external link won't open, possibly without any error message.
A work-around is to configure the desktop environment to open DTS files with
a text editor (e.g. with the *Open with* paradigm).

### Output redirection

Command output redirection uses the well-known syntax:

    CMD [OPTIONS] [PARAMS] > PATH

where `PATH` is the absolute or relative path to the file the command output will be redirected to.

Depending on the extension, the command output may be saved as an HTML page (`.html`),  an SVG image (`.svg`),
or a text file (default).

For example:

    /
    ❯ ls -l soc > soc.html

### Keybindings

Familiar keybindings are set through GNU readline integration.

- `C-l`    clear terminal screen
- `C-a`    move cursor to beginning of command line
- `C-e`    move cursor to end of command line
- `C-k`    *kill* text from cursor to end of command line
- `M-d`    *kill* word at cursor
- `C-y`    *yank* (paste) the content of the *kill buffer*
- `C-←`    move cursor one word backward
- `C-→`    move cursor one word forward
- `↑`      navigate the commands history backward
- `↓`      navigate the commands history forward
- `C-r`    search the commands history
- `TAB`    trigger auto-completion

### Theme

Colors and such are subjective, and most importantly the rendering will
eventually depend on the terminal&rsquo;s font and palette,
possibly resulting in severe accessibility issues, e.g. grey text on white background
or a weird shell prompt.

In such situations, or to accommodate personal preferences, users can try to override
`dtsh` colors (and prompt) by creating a *theme* file  (typically `$HOME/.config/dtsh/theme`).

Use the [default theme](https://github.com/dottspina/dtsh/blob/main/src/dtsh/theme) as template:

    cp src/dtsh/theme ~/.config/dtsh/theme

## References

**Devicetree Specifications**

-   [Online Devicetree Specifications](https://devicetree-specification.readthedocs.io/en/latest/) (latest)
-   [Online Devicetree Specifications](https://devicetree-specification.readthedocs.io/en/stable/) (stable)

**Zephyr**

-   [Introduction to devicetree](https://docs.zephyrproject.org/latest/build/dts/intro.html)
-   [Devicetree bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html)
-   [Bindings index](https://docs.zephyrproject.org/latest/build/dts/api/bindings.html)
-   [Zephyr-specific chosen nodes](https://docs.zephyrproject.org/latest/build/dts/api/api.html#zephyr-specific-chosen-nodes)
-   [Devicetree versus Kconfig](https://docs.zephyrproject.org/latest/build/dts/dt-vs-kconfig.html)

**Linux**

-   [Open Firmware and Devicetree](https://docs.kernel.org/devicetree/index.html)
-   [Device Tree Usage](https://elinux.org/Device_Tree_Usage)
-   [Device Tree Reference](https://elinux.org/Device_Tree_Reference)
-   [Device Tree What It Is](https://elinux.org/Device_Tree_What_It_Is)
"""
