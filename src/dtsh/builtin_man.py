# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'man' command."""


from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshVt
from dtsh.dtsh import DtshCommandUsageError, DtshCommandFailedError
from dtsh.man import DtshBuiltinManPage


class DtshBuiltinMan(DtshCommand):
    """Print current working node's path.

DESCRIPTION
The `man` command opens the *reference* manual page `PAGE`.

Currently, the only supported pages (aka man section) are devicetree
shell command names.

By default, `man` will page its output: use the **--no-pager** option to
disable the pager.

EXAMPLES
To open the `ls` manual page: `man ls`
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'man',
            "open a manual page",
            False,
            [
                DtshCommandOption('no pager', None, 'no-pager', None),
            ]
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [PAGE]'

    @property
    def with_no_pager(self) -> bool:
        return self.with_flag('--no-pager')

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)
        if len(self._params) == 0:
            raise DtshCommandUsageError(self, 'what manual page do you want?')
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return

        arg_page = self._params[0]

        builtin = self._dtsh.builtin(arg_page)
        if builtin:
            view = DtshBuiltinManPage(builtin)
            view.show(vt, self.with_no_pager)
            return

        raise DtshCommandFailedError(self, f'page not found: {arg_page}')

    def autocomplete_param(self, prefix: str) -> list:
        """Overrides DtshCommand.autocomplete_param().
        """
        return self._autocomplete_command_name(prefix)

    def _autocomplete_command_name(self, prefix: str) -> list[str]:
        completions = list[str]()
        if prefix.find('/') == -1:
            for cmd in self._dtsh.builtins:
                if cmd.name.startswith(prefix) and (len(cmd.name) > len(prefix)):
                    completions.append(cmd.name)
        return completions
