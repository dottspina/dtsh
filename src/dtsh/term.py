# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Rich terminal for devicetree shells."""

import readline

from rich.console import Console, PagerContext

from dtsh.dtsh import DtshVt
from dtsh.tui import DtshTui


class DevicetreeTerm(DtshVt):
    """Rich terminal for devicetree shells.

    Rich standard output and pager support with the Python rich library,
    standard input with GNU readline completion.
    """

    _console: Console
    _pager: PagerContext | None

    def __init__(self,
                 readline_comp_hook = None,
                 readline_display_hook = None) -> None:
        """Initialize a rich terminal.

        Creates a rich console and setup GNU readline completion support.

        Arguments:
        readline_comp_hook -- GNU readline completions hook or None
        readline_display_hook -- GNU readline display hook or None
        """
        # We do not want Console syntax highlighting by default.
        self._console = Console(highlight=False, theme=DtshTui.theme())
        self._pager = None

        if readline_comp_hook is not None:
            # Setup readline autocomp support.
            readline.set_completer(readline_comp_hook)
            # We want to treat '/' as part of a word
            readline.set_completer_delims(' \t\n')
            if readline_display_hook is not None:
                readline.set_completion_display_matches_hook(readline_display_hook)
            readline.parse_and_bind("tab: complete")

    def write(self, *args, **kwargs) -> None:
        """Overrides DtshVt.write()

        Print to rich console.

        See:
        - https://rich.readthedocs.io/en/stable/reference/console.html#rich.console.Console.print

        Arguments:
        args -- Positional arguments for Console.print()
        kwargs -- Keyword arguments for Console.print()
        """
        self._console.print(*args, **kwargs)

    def pager_enter(self) -> None:
        """Overrides DtshVt.pager_enter().
        """
        if self._pager is None:
            self._console.clear()
            self._pager = self._console.pager(styles=True, links=True)
            self._pager.__enter__()

    def pager_exit(self) -> None:
        """Overrides DtshVt.pager_exit().
        """
        if self._pager is not None:
            self._pager.__exit__(None, None, None)
            self._pager = None

    def clear(self) -> None:
        """Overrides DtshVt.clear().
        """
        self._console.clear()

    def readline(self, ansi_prompt: str) -> str:
        """Overrides DtshVt.readline().

        Arguments:
        ansi_prompt -- raw ANSI prompt (with ANSI codes)

        See:
        - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code
        """
        # Using rich.Console.input() with GNU readline enabled would 'eat' (remove)
        # the command prompt when navigating commands history.
        #
        # See:
        # - "Backspacing deletes the prompt in console.input using a custom theme"
        #   (https://github.com/Textualize/rich/issues/299)
        # - "Backspacing deletes the prompt in console.input using readline"
        #   (https://github.com/Textualize/rich/issues/2293)
        # - https://wiki.hackzine.org/development/misc/readline-color-prompt.html
        #
        # Will block till ENTER or EOF.
        cmdline = input(ansi_prompt)
        return cmdline.strip()

    def abort(self) -> None:
        """Overrides DtshVt.abort().
        """
        self._console.print()
