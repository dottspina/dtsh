# Copyright (c) 2025 Christophe Dufaza
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
from pathlib import Path

from west.commands import Verbosity, WestCommand

# Debug Python system path.
_dbg: bool = "DTSH_DBG" in os.environ

# Append dtsh package to system path,
# assuming DTSH_BASE/scripts/west_commands/dtsh_cmd.py
_dtsh_base = Path(__file__).parent.parent.parent
sys.path.append(os.fspath(_dtsh_base / "src"))

# ZEPHYR_BASE required to access Zephyr in-tree devicetree package,
# applying the same search method as zephyr_ext_common.py:
# - prefer environment variable if set
# - fallback to file-system paths manipulations,
#   here  assuming the module was installed to e.g. zephyrproject-rtos/modules/tools/dtsh,
#   and we'll find a valid ZEPHYR_BASE at zephyrproject-rtos/zephyr
# We insert rather than append to enforce we're using the in-tree package.
if "ZEPHYR_BASE" in os.environ:
    _zephyr_base = Path(os.environ["ZEPHYR_BASE"])
    if _dbg:
        print(f"ZEPHYR_BASE (environment): {_zephyr_base}", file=sys.stderr)
else:
    _zephyr_base = _dtsh_base.parent.parent.parent / "zephyr"
    if _dbg:
        print(f"ZEPHYR_BASE (workspace): {_zephyr_base}", file=sys.stderr)
sys.path.insert(0, os.fspath(_zephyr_base / "scripts" / "dts" / "python-devicetree" / "src"))

# Make sure we've found the Python devicetree package.
try:
    import devicetree

    if _dbg:
        print(f"Python devicetree: {os.path.dirname(devicetree.__file__)}", file=sys.stderr)
except ImportError as e:
    print(
        f"""Failed to import Python devicetree: {e}
Check that:
- either the ZEPHYR_BASE environment variable is set
- or the dtsh module is installed to <workspace>/modules/tools/dtsh""",
        file=sys.stderr,
    )
    sys.exit(1)

# At this point we should be able to import from dtsh.
from dtsh.cli import DTShArgvParser, DTShCli
from dtsh.shell import DTShError

_description = """\
Interactive DTS file viewer with a shell-like command line interface:
- easily navigate and visualize the devicetree
- find nodes based on e.g. supported bus protocols, bindings, generated IRQs,
  memory size, or keywords like 'sensor' or 'PWM'
- redirect commands output to files (text, HTML, SVG)
  to document hardware configurations or simply take notes
- scriptable (aka batch modes)
- contextual auto-completion, commands history, semantic highlighting, user profiles

Handbook: https://dottspina.github.io/dtsh/handbook.html
"""


class Dtsh(WestCommand):
    """DTSh West extension"""

    _parser: argparse.ArgumentParser

    def __init__(self, verbosity: Verbosity = Verbosity.INF) -> None:
        super().__init__(
            "dtsh",
            "Devicetree Shell",
            _description,
            accepts_unknown_args=False,
            verbosity=verbosity,
        )

    def do_add_parser(self, parser_adder) -> argparse.ArgumentParser:
        self._parser = parser_adder.add_parser(
            self.name,
            help=self.help,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.description,
        )
        DTShArgvParser.init(self._parser)
        return self._parser

    def do_run(self, args: argparse.Namespace, unknown: list[str]) -> None:
        del unknown  # Unused.

        cli = DTShCli(self._parser)
        try:
            cli.run(args)
        except DTShError as e:
            self.err(e.msg)
            self.die("Failed to initialize DTSh session, try 'west dtsh -h'.")
