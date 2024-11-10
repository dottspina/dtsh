# Copyright (c) 2023 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Rich I/O streams for devicetree shells.

- rich VT
- rich redirection streams for SVG and HTML

Rich I/O streams implementations are based on the rich.console module.
"""


from typing import Any, IO, List, Mapping, Optional, Sequence

from io import StringIO
import os

from rich.console import Console, PagerContext
from rich.measure import Measurement
from rich.theme import Theme
from rich.terminal_theme import (
    SVG_EXPORT_THEME,
    DEFAULT_TERMINAL_THEME,
    MONOKAI,
    DIMMED_MONOKAI,
    NIGHT_OWLISH,
    TerminalTheme,
)

from dtsh.config import DTShConfig
from dtsh.io import DTShVT, DTShInput, DTShOutput, DTShRedirect

from dtsh.rich.theme import DTShTheme
from dtsh.rich.svg import SVGDocument

_dtshconf: DTShConfig = DTShConfig.getinstance()
_theme: DTShTheme = DTShTheme.getinstance()


class DTShRichVT(DTShVT):
    """Rich terminal for devicetree shells."""

    _console: Console
    _pager: Optional[PagerContext]

    def __init__(self) -> None:
        """Initialize VT."""
        super().__init__()
        self._console = Console(theme=Theme(_theme.styles), highlight=False)
        self._pager = None

    def write(self, *args: Any, **kwargs: Any) -> None:
        """Write to rich console.

        Overrides DTShOutput.write().

        Args:
            *args: Positional arguments, Console.print() semantic.
            **kwargs: Keyword arguments, Console.print() semantic.

        """
        self._console.print(*args, **kwargs)

    def flush(self) -> None:
        """Flush rich console output without sending LF.

        Overrides DTShOutput.flush().
        """
        self._console.print("", end="")

    def clear(self) -> None:
        """Overrides DTShVT.clear()."""
        self._console.clear()

    def pager_enter(self) -> None:
        """Overrides DTShOutput.pager_enter()."""
        if not self._pager:
            self._console.clear()
            self._pager = self._console.pager(styles=True, links=True)
            # We have to explicitly enter the context since we need
            # more control on it than the context manager would permit.
            self._pager.__enter__()  # pylint: disable=unnecessary-dunder-call

    def pager_exit(self) -> None:
        """Overrides DTShOutput.pager_exit()."""
        if self._pager:
            self._pager.__exit__(None, None, None)
            self._pager = None


class DTShBatchRichVT(DTShRichVT):
    """Rich terminal for devicetree shells with batch mode support.

    Batch mode support, will:
    - first read command lines from the batch input stream until EOF
    - then, if interactive, read command lines from VT input stream until EOF
    """

    # Batch input stream, reset to None on EOF.
    _batch_istream: Optional[DTShInput]

    # Whether to read from VT after batch.
    _interactive: bool

    def __init__(self, batch_is: DTShInput, interactive: bool) -> None:
        """Initialize VT.

        Args:
            batch: Batch input stream.
            interactive: Whether to read from VT after batch
              (interactive sessions).
        """
        super().__init__()
        self._batch_istream = batch_is
        self._interactive = interactive

    def is_tty(self) -> bool:
        """Overrides DTShInput.is_tty()."""
        return self._batch_istream is None

    def readline(self, multi_prompt: Optional[Sequence[Any]] = None) -> str:
        """Overrides DTShVT.readline()."""
        if self._batch_istream:
            try:
                return self._batch_istream.readline(multi_prompt)
            except EOFError:
                # Exhausted batch input stream.
                self._batch_istream = None

        if not self._interactive:
            # Signal EOF if we don't continue in interactive mode.
            raise EOFError()
        return super().readline(multi_prompt)


class DTShOutputFile(DTShOutput):
    """Base output stream for redirecting commands output.

    Provides a Console object initialized for supporting this use case:
    - set initial width to the configured maximum
    - record what would otherwise be printed to the TTY
    - capture TTY output so that it's not also echoed to the TTY
    """

    # Records/captures outputs.
    _console: Console

    def __init__(self) -> None:
        """Initialize console for commands output redirection."""
        self._console = Console(
            highlight=False,
            theme=Theme(_theme.styles),
            record=True,
            # Set the console's width to the configured maximum,
            # sub-classes will strip the rich segments on flush().
            width=_dtshconf.pref_redir2_maxwidth,
            # Capture output: we don't want to echo the output to the TTY
            # when redirecting to files.
            file=StringIO(),
        )

    def write(self, *args: Any, **kwargs: Any) -> None:
        """Capture and record outputs.

        Overrides DTShOutput.write().

        Args:
            *args: Positional arguments, Console.print() semantic.
            **kwargs: Keyword arguments, Console.print() semantic.
        """
        self._console.print(*args, **kwargs)


class DTShOutputFileText(DTShOutputFile):
    """Text output file for commands output redirection."""

    _out: IO[str]

    def __init__(self, path: str, append: bool) -> None:
        """Initialize output file.

        Args:
            path: The output file path.
            append: Whether to redirect the command's output in "append" mode.

        Raises:
             DTShRedirect.Error: Invalid path or permission errors.
        """
        super().__init__()
        try:
            # Early initialize output stream rather than handling that on flush.
            self._out = open(  # pylint: disable=consider-using-with
                path,
                "a" if append else "w",
                encoding="utf-8",
            )
            if append:
                # Insert blank line between command outputs.
                self._out.write(os.linesep)
        except OSError as e:
            raise DTShRedirect.Error(e.strerror) from e

    def flush(self) -> None:
        """Format (HTML) the captured output and write it
        to the redirection file.

        Overrides DTShOutput.flush().
        """
        contents = self._console.export_text()
        # Exported lines are padded up to the (maximum) console width:
        # strip these trailing whitespaces, which could make the text file
        # unreadable.
        for line_nopad in (line.rstrip() for line in contents.splitlines()):
            print(line_nopad, file=self._out)
        self._out.close()


class DTShOutputFileHtml(DTShOutputFile):
    """HTML output file for commands output redirection."""

    _out: IO[str]
    _append: bool

    # True until we call write() to actually capture something.
    # If flush() is called before that, e.g. because the DTSh command failed,
    # it will abort early.
    _pending: bool = True

    def __init__(self, path: str, append: bool) -> None:
        """Initialize output file.

        Args:
            path: The output file path.
            append: Whether to redirect the command's output in "append" mode.

        Raises:
             DTShRedirect.Error: Invalid path or permission errors.
        """
        super().__init__()
        self._append = append

        # Early initialize the redirection stream and fail now on
        # OS errors: we won't run a DTSh command whose result no one
        # will ever see.
        try:
            self._out = open(  # pylint: disable=consider-using-with
                path,
                "r+" if append else "w",
                encoding="utf-8",
            )
        except OSError as e:
            raise DTShRedirect.Error(e.strerror) from e

    def _mk_html_format(self) -> str:
        font_family = _dtshconf.pref_html_font_family
        if font_family:
            font_family = f"{font_family},monospace"
        else:
            font_family = "monospace"
        html_fmt = DTSH_HTML_META_FORMAT.replace("|font_family|", font_family)

        html_fmt = html_fmt.replace(
            # "medium" is the default (absolute) size.
            "|font_size|",
            _dtshconf.pref_html_font_size or "medium",
        )

        return html_fmt

    def write(self, *args: Any, **kwargs: Any) -> None:
        """Capture and record outputs.

        Overrides DTShOutputFile.write().

        Args:
            *args: Positional arguments, Console.print() semantic.
            **kwargs: Keyword arguments, Console.print() semantic.
        """
        if self._pending:
            if self._append:
                # When appending to an existing content (output file),
                # insert a blank line before we start to actually
                # capture the last command output.
                #
                # NOTE: we can't do that on flush, it will be too late,
                # the capture starts right bellow.
                if not _dtshconf.pref_html_compact:
                    super().write()
            # Capture is ongoing.
            self._pending = False

        super().write(*args, **kwargs)

    def flush(self) -> None:
        """Format (HTML) the captured output and write it
        to the redirection file.

        Overrides DTShOutput.flush().
        """
        if self._pending:
            # Calling write() without argument or with empty rich objects
            # would append an unwanted blank line.
            self._out.close()
            return

        # Text and background colors.
        theme = DTSH_EXPORT_THEMES.get(
            _dtshconf.pref_html_theme, DEFAULT_TERMINAL_THEME
        )

        html_fmt = self._mk_html_format()

        html = self._console.export_html(
            theme=theme,
            code_format=html_fmt,
            # Use inline CSS styles in "append" mode.
            inline_styles=self._append,
        )

        # The generated HTML pad lines with withe spaces
        # up to the console's width, which is ugly if you
        # want to re-use the HTML source: clean this up.
        html_lines: List[str] = [line.rstrip() for line in html.splitlines()]

        # Index of the first line we'll write to the HTML output file:
        # - either 0, pointing to the first line for the current redirection
        #   contents, if we're creating a new file
        # - or, in "append" mode, the index of the line containing
        #   the <pre> tag that represents the actual command's output
        #
        # Since this <pre> tag appears immediately before the HTML epilog,
        # we'll then just have to write the current re-direction's contents
        # starting from this index.
        i_output: int = 0

        if self._append:
            # Appending to an existing file: seek to the appropriate
            # point of insertion.
            self._seek_last_content()
            self._out.write(os.linesep)

            # Find command's output contents.
            for i, line in enumerate(html_lines):
                if line.find("<pre") != -1:
                    i_output = i
                    break

        for line in html_lines[i_output:]:
            print(line, file=self._out)
        self._out.close()

    def _seek_last_content(self) -> None:
        # Offset for the point of insertion, just before the HTML epilog.
        offset: int = self._out.tell()
        line = self._out.readline()
        while line and not line.startswith("</body>"):
            offset = self._out.tell()
            line = self._out.readline()
        self._out.seek(offset, os.SEEK_SET)


class DTShOutputFileSVG(DTShOutputFile):
    """SVG output file for commands output redirection."""

    _out: IO[str]
    _append: bool

    _maxwidth: int
    _width: int

    def __init__(self, path: str, append: bool) -> None:
        """Initialize output file.

        Args:
            path: The output file path.
            append: Whether to redirect the command's output in "append" mode.

        Raises:
             DTShRedirect.Error: Invalid path or permission errors.
        """
        super().__init__()
        self._append = append

        # Early initialize the redirection stream and fail now on
        # OS errors: we won't run a DTSh command whose result no one
        # will ever see.
        try:
            self._out = open(  # pylint: disable=consider-using-with
                path,
                "r+" if append else "w",
                encoding="utf-8",
            )
        except OSError as e:
            raise DTShRedirect.Error(e.strerror) from e

        # Maximum width allowed in preferences.
        self._maxwidth = _dtshconf.pref_redir2_maxwidth

        # Width required to output the command's output without wrapping or
        # cropping, up to the configured maximum.
        self._width = 0

    def write(self, *args: Any, **kwargs: Any) -> None:
        """Record/capture output.

        Overrides DTShOutput.write().

        Args:
            *args: Positional arguments, Console.print() semantic.
            **kwargs: Keyword arguments, Console.print() semantic.
        """
        if self._append and not self._width:
            # When appending to an existing content (output file),
            # insert a blank line before we start to atually
            # capture the last command output.
            #
            # NOTE: we can't do that on flush, it will be too late,
            # the capture starts right bellow (that's how we can compute
            # the actual width of the command output).
            if not _dtshconf.pref_svg_compact:
                super().write()

        # Write output to console using the maximum width.
        super().write(*args, **kwargs)

        # Update actually required width.
        for arg in args:
            if (
                isinstance(arg, str)
                # Aka RichCast.
                or hasattr(arg, "__rich__")
                # Aka ConsoleRenderable.
                or hasattr(arg, "__rich_console__")
            ):
                measure = Measurement.get(
                    self._console, self._console.options, arg
                )
                if (measure.maximum > self._width) and not (
                    measure.maximum > self._maxwidth
                ):
                    self._width = measure.maximum

    def flush(self) -> None:
        """Format (SVG) the captured output and write it
        to the redirection file.

        Overrides DTShOutput.flush().
        """
        if not self._width:
            # Calling write() without argument or with empty rich objects
            # would append an unwanted blank line.
            self._out.close()
            return

        # Text and background colors.
        theme = DTSH_EXPORT_THEMES.get(
            _dtshconf.pref_svg_theme, DEFAULT_TERMINAL_THEME
        )

        # Shrink the console's width, to prevent the SVG document from being
        # unnecessarily wide.
        self._console.width = self._width

        # Get captured command output as SVG.
        svg_capture: SVGDocument = SVGDocument.capture(
            self._console,
            font_family=_dtshconf.pref_svg_font_family,
            font_ratio=_dtshconf.pref_svg_font_ratio,
            theme=theme,
            title=_dtshconf.pref_svg_title,
            show_gcircles=_dtshconf.pref_svg_decorations,
        )

        svg_doc: SVGDocument
        if self._append:
            # Load the SVG content we're appending to.
            svg_doc = SVGDocument(
                self._out.read().splitlines(),
                len(_dtshconf.pref_svg_title) > 0,
                _dtshconf.pref_svg_decorations,
            )
            self._out.seek(0, os.SEEK_SET)
            # Append the last command output capture.
            svg_doc.append(svg_capture)
        else:
            svg_doc = svg_capture

        for line in svg_doc.content:
            print(line, file=self._out)

        if self._append:
            # Append mode, cleanup once we're done.
            offset: int = self._out.tell()
            self._out.truncate(offset)

        self._out.close()


DTSH_HTML_META_FORMAT = """\
<!DOCTYPE html>
<html>

<head>
<meta charset="UTF-8">

<style>
{stylesheet}
body {{
    color: {foreground};
    background-color: {background};
}}
</style>
</head>

<body>

    <pre style="font-family:|font_family|; font-size:|font_size|"><code style="font-family:inherit">{code}</code></pre>

</body>

</html>
"""

# See also: rich._export_format.CONSOLE_SVG_FORMAT
DTSH_SVG_META_FORMAT = """\
<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>

    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Regular"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff") format("woff");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Bold"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff") format("woff");
        font-style: bold;
        font-weight: 700;
    }}

    .{unique_id}-matrix {{
        font-family: |font_family|;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
    }}

    .{unique_id}-title {{
        font-size: 18px;
        font-weight: bold;
        font-family: arial;
    }}

    {styles}
    </style>

    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />
    </clipPath>
    {lines}
    </defs>

    {chrome}
    <g transform="translate({terminal_x}, {terminal_y})" clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
    </g>
    </g>
</svg>
"""


DTSH_EXPORT_THEMES: Mapping[str, TerminalTheme] = {
    "svg": SVG_EXPORT_THEME,
    "html": DEFAULT_TERMINAL_THEME,
    "dark": DIMMED_MONOKAI,
    "light": NIGHT_OWLISH,
    "night": MONOKAI,
}
