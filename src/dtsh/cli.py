# Copyright (c) 2023 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell CLI.

Run the devicetree shell without West.
"""

from typing import cast, Optional, Union, List

import argparse
import os
import sys

from dtsh.config import DTShConfig
from dtsh.shell import DTShError
from dtsh.rich.theme import DTShTheme
from dtsh.rich.session import DTShRichSession


class DTShCliArgv:
    """Command line arguments parser."""

    _parser: argparse.ArgumentParser
    _argv: argparse.Namespace

    def __init__(self) -> None:
        self._parser = argparse.ArgumentParser(
            prog="dtsh",
            description="shell-like interface with Devicetree",
            # See e.g. https://github.com/zephyrproject-rtos/zephyr/issues/53495
            allow_abbrev=False,
        )

        grp_open_dts = self._parser.add_argument_group("open a DTS file")
        grp_open_dts.add_argument(
            "-b",
            "--bindings",
            help="directory to search for binding files",
            action="append",
            metavar="DIR",
        )
        grp_open_dts.add_argument(
            "dts", help="path to the DTS file", nargs="?", metavar="DTS"
        )

        grp_user_files = self._parser.add_argument_group("user files")
        grp_user_files.add_argument(
            "-u",
            "--user-files",
            help="initialize per-user configuration files and exit",
            action="store_true",
        )
        grp_user_files.add_argument(
            "--preferences",
            help="load additional preferences file",
            metavar="FILE",
        )
        grp_user_files.add_argument(
            "--theme",
            help="load additional styles file",
            metavar="FILE",
        )

        grp_session_ctrl = self._parser.add_argument_group("session control")
        grp_session_ctrl.add_argument(
            "-c",
            help="execute CMD at startup (may be repeated)",
            action="append",
            metavar="CMD",
        )
        grp_session_ctrl.add_argument(
            "-f",
            help="execute batch commands from FILE at startup",
            metavar="FILE",
        )
        grp_session_ctrl.add_argument(
            "-i",
            "--interactive",
            help="enter interactive loop after batch commands",
            action="store_true",
        )

        self._argv = self._parser.parse_args()
        if self._argv.f and self._argv.c:
            self._parser.error("-c and -f are mutually exclusive")

    @property
    def binding_dirs(self) -> Optional[List[str]]:
        """Directories to search for binding files."""
        if self._argv.bindings:
            return cast(List[str], self._argv.bindings)
        return None

    @property
    def dts(self) -> str:
        """Path to the Devicetree source file."""
        if self._argv.dts:
            return cast(str, self._argv.dts)
        return os.path.join(os.path.abspath("build"), "zephyr", "zephyr.dts")

    @property
    def user_files(self) -> bool:
        """Initialize user files and exit."""
        return bool(self._argv.user_files)

    @property
    def preferences(self) -> Optional[str]:
        """Additional preferences file."""
        if self._argv.preferences:
            return cast(str, self._argv.preferences)
        return None

    @property
    def theme(self) -> Optional[str]:
        """Additional styles file."""
        if self._argv.theme:
            return cast(str, self._argv.theme)
        return None

    @property
    def batch_source(self) -> Optional[Union[str, List[str]]]:
        """Batch command source, if defined."""
        if self._argv.c:
            return cast(List[str], self._argv.c)
        if self._argv.f:
            return cast(str, self._argv.f)
        return None

    @property
    def interactive(self) -> bool:
        """Is the interactive loop requested?"""
        if not (self._argv.c or self._argv.f):
            # no batch input, must be interactive
            return True
        return cast(bool, self._argv.interactive)


def _load_preference_file(path: str) -> None:
    try:
        DTShConfig.getinstance().load_ini_file(path)
    except DTShConfig.Error as e:
        print(f"Failed to load preferences file: {path}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(-22)


def _load_theme_file(path: str) -> None:
    try:
        DTShTheme.getinstance().load_theme_file(path)
    except DTShTheme.Error as e:
        print(f"Failed to load styles file: {path}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(-22)


def run() -> None:
    """Open a devicetree shell session and run batch commands
    and/or its interactive loop.
    """
    argv = DTShCliArgv()

    if argv.user_files:
        # Initialize per-user configuration files and exit.
        ret = DTShConfig.getinstance().init_user_files()
        sys.exit(ret)

    if argv.preferences:
        # Load additional preference file.
        _load_preference_file(argv.preferences)

    if argv.theme:
        # Load additional styles file.
        _load_theme_file(argv.theme)

    session = None
    try:
        if argv.batch_source:
            session = DTShRichSession.create_batch(
                argv.dts, argv.binding_dirs, argv.batch_source, argv.interactive
            )
        else:
            session = DTShRichSession.create(argv.dts, argv.binding_dirs)
    except DTShError as e:
        print("Failed to initialize devicetree:", file=sys.stderr)
        print(e.msg, file=sys.stderr)
        sys.exit(-22)

    if session:
        session.run(argv.interactive)


if __name__ == "__main__":
    run()
