# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Shell configuration API."""


import os
import sys

from rich.theme import Theme

from dtsh.rl import readline
from dtsh.dtsh import DtshError


class DtshConfig(object):
    """Shell configuration manager.
    """

    @staticmethod
    def usr_config_base_posix() -> str:
        """User configuration directory (Linux).

        On Linux, the user configuration is $XDG_CONFIG_HOME/dtsh.

        According to the XDG Base Directory Specification,
        should default to ~/.config/dtsh if XDG_CONFIG_HOME is not set.

        See:
        - https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
        """
        cfg_base = os.environ.get('XDG_CONFIG_HOME')
        if not cfg_base:
            cfg_base = os.path.join(os.path.expanduser('~'), '.config')
        return os.path.join(cfg_base, 'dtsh')

    @staticmethod
    def usr_config_base_nt() -> str:
        r"""User configuration directory (Windows).

        On Windows (NT+), the user configuration is %LOCALAPPDATA%\dtsh,
        and should default to ~\AppData\Local\Dtsh.
        """
        cfg_base = os.environ.get('LOCALAPPDATA')
        if not cfg_base:
            cfg_base = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
        return os.path.join(cfg_base, 'Dtsh')

    @staticmethod
    def usr_config_base_darwin() -> str:
        """User configuration directory (macOS).

        On macOS, default to ~/Library/Dtsh.
        """
        return os.path.join(os.path.expanduser('~'), 'Libray', 'Dtsh')

    @staticmethod
    def usr_config_base(enforce: bool = False) -> str:
        """Returns the user's configuration directory for dtsh sessions.

        Arguments:
        enforce -- if True, will try to create the configuration directory
                   when necessary

        Raises IOError when the requested directory can't be initialized.
        """
        if sys.platform == 'darwin':
            cfg_dir = DtshConfig.usr_config_base_darwin()
        elif os.name == 'nt':
            cfg_dir = DtshConfig.usr_config_base_nt()
        else:
            cfg_dir = DtshConfig.usr_config_base_posix()
        if enforce and not os.path.isdir(cfg_dir):
            os.mkdir(cfg_dir)
        return cfg_dir

    @staticmethod
    def get_history_path() -> str:
        """Returns the history file's path.

        Raises IOError when the configuration directory can't be initialized.
        """
        return os.path.join(DtshConfig.usr_config_base(True), 'history')

    @staticmethod
    def get_theme_path() -> str:
        """Returns the rich theme's path.
        """
        theme_path = os.path.join(DtshConfig.usr_config_base(), 'theme')
        if not os.path.isfile(theme_path):
            # Fallback to default theme.
            theme_path = os.path.join(os.path.dirname(__file__), 'theme')
        return theme_path

    @staticmethod
    def readline_read_history() -> None:
        """Load history file.
        """
        try:
            history_path = DtshConfig.get_history_path()
            if os.path.isfile(history_path):
                readline.read_history_file(history_path)
        except IOError as e:
            print(f"Failed to load history: {str(e)}")

    @staticmethod
    def readline_write_history() -> None:
        """Save history file.
        """
        try:
            readline.write_history_file(DtshConfig.get_history_path())
        except IOError as e:
            print(f"Failed to save history: {str(e)}")

    @staticmethod
    def rich_read_theme() -> Theme:
        """Returns the rich theme.

        Raises DtshError when the theme file is invalid.
        """
        try:
            return Theme.from_file(open(DtshConfig.get_theme_path()))
        except Exception as e:
            raise DtshError("Failed to load theme", e)
