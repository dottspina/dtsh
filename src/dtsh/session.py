# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell session."""


import os
import re
import readline
import signal
import sys

from devicetree.edtlib import Node, Binding, Property

from rich.console import Console
from rich.text import Text

from dtsh.dtsh import Dtsh, DtshAutocomp, DtshCommand, DtshCommandOption, DtshSession, DtshVt
from dtsh.dtsh import DtshError, DtshCommandNotFoundError, DtshCommandUsageError, DtshCommandFailedError
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
            redir2vt = None
            try:
                self._term.write(DtshTui.mk_txt_node_path(self._dtsh.pwd))
                prompt = DtshTui.mk_ansi_prompt(self._last_err is not None)
                cmdline = self._term.readline(prompt)
                self._last_err = None
                if cmdline:
                    if cmdline in ['q', 'quit', 'exit']:
                        # Exit process.
                        self.close()

                    i = cmdline.rfind('>')
                    if i != -1:
                        redir2vt = FileStdoutVt(cmdline[i+1:].strip())
                        self._dtsh.exec_command_string(cmdline[:i], redir2vt)
                    else:
                        self._dtsh.exec_command_string(cmdline, self._term)

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

            if redir2vt:
                # Actually writing to the file happens in the VT dtor.
                del redir2vt
                redir2vt = None
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
        self._term.write(
            Text().append_tokens(
                [
                    ('dtsh', DtshTui.style_bold()),
                    (f" ({Dtsh.API_VERSION}): ", DtshTui.style_default()),
                    ('Shell-like interface to a devicetree', DtshTui.style_italic())
                ]
            )
        )
        self._term.write(
            Text().append_tokens(
                [
                    ('Help: ', DtshTui.style_default()),
                    ('man dtsh', DtshTui.style_bold())
                ]
            )
        )
        self._term.write(
            Text().append_tokens(
                [
                    ('How to exit: ', DtshTui.style_default()),
                    ('q', DtshTui.style_bold()),
                    (', or ', DtshTui.style_default()),
                    ('quit', DtshTui.style_bold()),
                    (', or ', DtshTui.style_default()),
                    ('exit', DtshTui.style_bold()),
                    (', or press ', DtshTui.style_default()),
                    ('Ctrl-D', DtshTui.style_bold()),
                ]
            )
        )
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



class FileStdoutVt(DtshVt):
    """VT implementation for command output redirection.
    """

    _console: Console


    def __init__(self, path: str) -> None:
        """ Creates a new VT.

        Arguments:
        path -- Path of the file the command output is redirected to;
                the file format (HTML, SVG, text) is determined by the filename
                extension (.html, .svg, default).
        """
        try:
            path = os.path.abspath(path)
            self._file = open(path, 'w')
        except IOError as e:
            raise DtshError(f'could not open file: {path}', e)
        self._console = Console(highlight=False,
                                theme=DtshTui.theme(),
                                record=True)

    def pager_enter(self) -> None:
        """Overrides DtshVt.pager_enter().

        Ignored, no pager.
        """
        pass

    def pager_exit(self) -> None:
        """Overrides DtshVt.pager_exit().

        Ignored, no pager.
        """
        pass

    def write(self, *args, **kwargs) -> None:
        """Overrides DtshVt.write().

        Quietly write to console, recording output.

        Arguments:
        args -- Positional arguments for Console.print()
        kwargs -- Keyword arguments for Console.print()
        """
        with self._console.capture():
            self._console.print(*args, **kwargs)

    def clear(self) -> None:
        """Overrides DtshVt.clear().

        Ignored, does not clear the console.
        """
        pass

    def readline(self, ansi_prompt: str) -> str:
        """Overrides DtshVt.readline().

        Returns an empty string (no input stream).
        """
        return ''

    def abort(self) -> None:
        """Overrides DtshVt.abort().

        Ignored.
        """
        pass

    # Actually writing to file happens in he dtor.
    #
    def __del__(self):
        if self._file.name.endswith('.html'):
            html = self._console.export_html()
            self._file.write(html)
        elif self._file.name.endswith('.svg'):
            self._write_svg()
        else:
            txt = self._console.export_text()
            self._file.write(txt)
        self._file.close()

    def _write_svg(self):
        svg = self._console.export_svg(title='')
        # Remove macOS-ish windows buttons.
        s = re.search(_RE_SVG_BUTTONS, svg)
        if s:
            svg = svg[:s.start()] + svg[s.end() + 1:]
        # Remove top padding
        svg_vstr = list[str]()
        re_view = re.compile(_RE_SVG_VIEWPORT)
        re_rect = re.compile(_RE_SVG_RECT)
        re_trans = re.compile(_RE_SVG_TRANSFORM)
        for line in svg.splitlines(keepends=True):
            # Substract hard coded padding to viewport's height.
            m = re_view.match(line)
            if m and m.groups():
                width = m.groups()[0]
                height = m.groups()[1]
                line = line.replace(
                    f'viewBox="0 0 {width} {height}"',
                    f'viewBox="0 0 {width} {float(height) - _SVG_HARD_PADDING}"'
                )

            # Substract hard coded padding to viewport's height.
            m = re_rect.match(line)
            if m and m.groups():
                height = m.groups()[0]
                line = line.replace(
                    f'height="{height}"',
                    f'height="{float(height) - _SVG_HARD_PADDING}"')

            # Substract hard coded padding to transformation y.
            m = re_trans.match(line)
            if m and m.groups():
                x = m.groups()[0]
                y = m.groups()[1]
                line = line.replace(
                    f'translate({x}, {y})',
                    f'translate({x}, {int(y) - _SVG_HARD_PADDING})'
                )

            svg_vstr.append(line)

        self._file.writelines(svg_vstr)


# Hard coded top padding in rich.console.export_svg().
#
_SVG_HARD_PADDING = 40

# All values in this regex are hard coded in rich.console.export_svg(),
# and do not seem to depen on e.g. a theme.
# We'll remove the whole pattern.
_RE_SVG_BUTTONS = r'''<g transform="translate\(26,22\)">\s*<circle cx="0" cy="0" r="7" fill="#ff5f57"/>\s*<circle cx="22" cy="0" r="7" fill="#febc2e"/>\s*<circle cx="44" cy="0" r="7" fill="#28c840"/>\s*</g>'''

# We'll substract the hard coded padding to the viewport height (the second group).
_RE_SVG_VIEWPORT = r'''\s*<svg class="rich-terminal" viewBox="0 0 (\S*) (\S*)" xmlns="http://www.w3.org/2000/svg">\s*'''

# We'll substract the hard coded padding to the rect height.
_RE_SVG_RECT = r'''\s*<rect fill="#\d*" stroke="rgba\(\d*,\d*,\d*,0\.\d*\)" stroke-width="1" x="1" y="1" width="\d*" height="(\d*\.\d*)" rx="\d*"/>\s*'''

# We'll substract the hard coded padding to the transformation y (the second group).
_RE_SVG_TRANSFORM = r'''\s*<g transform="translate\((\d*), (\d*)\)" clip-path="url\(#terminal-\d*-clip-terminal\)">\s*'''
