# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Shell configuration API."""


import os
import readline

from rich.theme import Theme

from dtsh.dtsh import DtshError


class DtshConfig(object):
    """Shell configuration manager.
    """

    @staticmethod
    def xdg_config_home(enforce: bool = False) -> str:
        """Returns the user's configuration directory for dtsh sessions.

        Arguments:
        enforce -- if True, will try to create the configuration directory
                   when necessary

        Raises IOError when the requested directory can't be initialized.
        """
        cfg_dir = os.environ.get('XDG_CONFIG_HOME')
        if not cfg_dir:
            cfg_dir = os.path.join(os.path.expanduser('~'), '.config')
        cfg_dir = os.path.join(cfg_dir, 'dtsh')
        if enforce and not os.path.isdir(cfg_dir):
            os.mkdir(cfg_dir)
        return cfg_dir

    @staticmethod
    def get_history_path() -> str:
        """Returns the history file's path.

        Raises IOError when the configuration directory can't be initialized.
        """
        return os.path.join(DtshConfig.xdg_config_home(True), 'history')

    @staticmethod
    def get_theme_path() -> str:
        """Returns the rich theme's path.
        """
        theme_path = os.path.join(DtshConfig.xdg_config_home(), 'theme')
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
