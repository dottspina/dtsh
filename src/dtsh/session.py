# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell session."""

import os
import readline
import signal
import sys

from devicetree.edtlib import Node, Binding, Property

from rich.text import Text

from dtsh.dtsh import Dtsh, DtshAutocomp, DtshCommand, DtshCommandOption, DtshSession, DtshError
from dtsh.dtsh import DtshCommandNotFoundError, DtshCommandUsageError, DtshCommandFailedError
from dtsh.shell import DevicetreeShell
from dtsh.term import DevicetreeTerm
from dtsh.autocomp import DevicetreeAutocomp
from dtsh.tui import DtshTui


class DevicetreeShellSession(DtshSession):
    """Shell session with GNU readline history support.
    """

    _dtsh: Dtsh
    _term: DevicetreeTerm
    _last_err: DtshError | None

    def __init__(self, shell: Dtsh, term: DevicetreeTerm) -> None:
        """Creates a session.

        Arguments:
        shell - the session's shell instance
        term - the session's rich VT
        """
        self._dtsh = shell
        self._term = term
        self._last_err = None

        self.readline_read_history()

    @property
    def term(self) -> DevicetreeTerm:
        """Session's VT."""
        return self._term

    @property
    def last_err(self) -> DtshError | None:
        return self._last_err

    def run(self):
        """Overrides DtshSession.run().
        """
        self._term.clear()
        self.banner()

        while True:
            try:
                self._term.write(DtshTui.mk_txt_node_path(self._dtsh.pwd))
                prompt = DtshTui.mk_ansi_prompt(self._last_err is not None)
                cmdline = self._term.readline(prompt)
                if cmdline:
                    if cmdline in ['q', 'quit', 'exit']:
                        self.close()
                    self._dtsh.exec_command_string(cmdline, self._term)
                    self._last_err = None
                else:
                    # Also reset error state on empty command line.
                    self._last_err = None

            except DtshCommandNotFoundError as e:
                self._last_err = e
                self._term.write(f'dtsh: Command not found: {e.name}')
            except DtshCommandUsageError as e:
                self._last_err = e
                self._term.write(f'{e.command.name}: {e.msg}')
            except DtshCommandFailedError as e:
                self._last_err = e
                self._term.write(f'{e.command.name}: {e.msg}')
            except EOFError:
                self._term.abort()
                self.close()
            if DtshTui.PROMPT_SPARSE:
                self._term.write()

    def close(self) -> None:
        """Overrides DtshSession.close().
        """
        self._term.write('bye.', style=DtshTui.style_italic())
        self.readline_write_history()
        sys.exit(0)

    def banner(self):
        """
        """
        view = Text().append_tokens(
            [
                ('dtsh', DtshTui.style_bold()),
                (f" ({Dtsh.API_VERSION}): ", DtshTui.style_default()),
                ('Shell-like interface to a devicetree', DtshTui.style_italic())
            ]
        )
        self._term.write(view)
        self._term.write()

    def readline_hist_path(self) -> str:
        return os.path.join(Dtsh.cfg_dir_path(), 'history')

    def readline_read_history(self):
        hist_path = self.readline_hist_path()
        if os.path.isfile(hist_path):
            readline.read_history_file(hist_path)

    def readline_write_history(self):
        cfg_path = Dtsh.cfg_dir_path()
        if not os.path.isdir(cfg_path):
            os.mkdir(cfg_path)
        readline.write_history_file(self.readline_hist_path())

    @staticmethod
    def open(dt_source_path: str | None = None,
             dt_bindings_path: list[str] | None = None) -> DtshSession:
        """
        """
        global _session
        global _autocomp

        if _session is not None:
            raise DtshError('Session already opened')

        shell = DevicetreeShell.create(dt_source_path, dt_bindings_path)
        term = DevicetreeTerm(
            readline_completions_hook,
            readline_display_hook
        )
        _session = DevicetreeShellSession(shell, term)
        _autocomp = DevicetreeAutocomp(shell)

        # We disable SIGINT (CTRL-C event).
        signal.signal(signal.SIGINT, dtsh_session_sig_handler)

        return _session


# Shell session singleton state.
_session: DevicetreeShellSession | None = None
_autocomp: DevicetreeAutocomp | None = None


# GNU readline completer function callback for rl_completion_matches().
# MUST answer completions that actually match te given prefix.
def readline_completions_hook(text: str, state: int) -> str | None:
    if _autocomp is None:
        return None

    cmdline = readline.get_line_buffer()
    completions = _autocomp.autocomplete(cmdline, text, 0)

    if state < len(completions):
        hint = completions[state]
        if len(completions) == 1:
            # GNU readline will eventually replace 'text' with these
            # state values (or their longest prefix).
            # When there's only one possible completion,
            # we can tell the user it's useless to press TAB again
            # by appending a space to the corresponding 'state' value.
            #
            # We assume a hint that ends with '/':
            # - is a node path
            # - the node has children, pressing TAB again should show them
            if not hint.endswith('/'):
                hint += ' '
        return hint

    return None


# GNU readline implementation for rl_completion_display_matches_hook().
#
def readline_display_hook(substitution, matches, longest_match_length) -> None:
    if (_session is None) or (_autocomp is None):
        return

    cmdline = readline.get_line_buffer()

    # Go bellow input line
    _session.term.write()

    if _autocomp.model:
        if _autocomp.mode == DtshAutocomp.MODE_DTSH_CMD:
            model = list[DtshCommand](_autocomp.model)
            view = DtshTui.mk_command_hints_display(model)
        elif _autocomp.mode == DtshAutocomp.MODE_DTSH_OPT:
            model = list[DtshCommandOption](_autocomp.model)
            view = DtshTui.mk_option_hints_display(model)
        elif _autocomp.mode == DtshAutocomp.MODE_DT_BINDING:
            model = list[Binding](_autocomp.model)
            view = DtshTui.mk_binding_hints_display(model)
        elif _autocomp.mode == DtshAutocomp.MODE_DT_NODE:
            model = list[Node](_autocomp.model)
            view = DtshTui.mk_node_hints_display(model)
        elif _autocomp.mode == DtshAutocomp.MODE_DT_PROP:
            model = list[Property](_autocomp.model)
            view = DtshTui.mk_property_hints_display(model)
        else:
            # Autcomp mode MODE_ANY.
            view = DtshTui.mk_grid(1)
            for m in _autocomp.model:
                view.add_row(DtshTui.mk_txt(str(m)))
        _session.term.write(view)

    _session.term.write(DtshTui.mk_ansi_prompt(), end='')
    _session.term.write(cmdline, end='')
    sys.stdout.flush()


def dtsh_session_sig_handler(signum, frame):
    # FIXME: closing() the session when the pager is active
    # breaks the TTY.
    # As a work-around, we ignore SIGINT.
    if signum == signal.SIGINT:
        return
