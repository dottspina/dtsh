# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'man' command."""

import readline
from typing import Tuple

from devicetree.edtlib import Binding

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshAutocomp, DtshVt
from dtsh.dtsh import DtshError, DtshCommandUsageError, DtshCommandFailedError
from dtsh.man import DtshManPageBinding, DtshManPageBuiltin, DtshManPageDtsh


class DtshBuiltinMan(DtshCommand):
    """Print current working node's path.

DESCRIPTION
The `man` command opens the *reference* manual page `PAGE`,
where `PAGES`:

- is either a devicetree shell built-in (e.g. `tree`)
- or a [*compatible*](https://devicetree-specification.readthedocs.io/en/latest/chapter2-devicetree-basics.html#compatible)
  specification if the **--compat** option is set

By default, `man` will page its output: use the **--no-pager** option to
disable the pager.

EXAMPLES
To open the `ls` shell built-in's manual page:

```
/
❯ man ls

```

To open a the manual page for a DT compatible (ARMv7-M NVIC):

```
/
❯ man --compat arm,v7m-nvic

```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'man',
            "open a manual page",
            # Won't support the --pager option, since enabled by default for
            # man pages (see --no-pager).
            False,
            [
                DtshCommandOption("page for a DT compatible", None, 'compat', None),
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
    def with_compat(self) -> bool:
        return self.with_flag('--compat')

    @property
    def with_no_pager(self) -> bool:
        return self.with_flag('--no-pager')

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) == 0:
            raise DtshCommandUsageError(self, 'what manual page do you want?')
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

        arg_page = self._params[0]

        man_page = None

        if self.with_compat:
            binding = self._dtsh.dt_bindings.get(arg_page)
            if binding:
                man_page = DtshManPageBinding(binding)
        else:
            builtin = self._dtsh.builtin(arg_page)
            if builtin:
                man_page = DtshManPageBuiltin(builtin)

        if (not man_page) and (arg_page == 'dtsh'):
            man_page = DtshManPageDtsh()

        if man_page is not None:
            man_page.show(vt, self.with_no_pager)
        else:
            raise DtshCommandFailedError(self, f'page not found: {arg_page}')

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        # 1st, complete according to flags.
        cmdline = readline.get_line_buffer()
        cmdline_vstr = cmdline.split()
        if len(cmdline_vstr) > 1:
            argv = cmdline_vstr[1:]
            try:
                self.parse_argv(argv)
            except DtshError:
                # Dry parsing of incomplete command line.
                pass
            if self.with_compat:
                completions = self._autocomplete_dt_binding(prefix)
                if completions:
                    return (DtshAutocomp.MODE_DT_BINDING, completions)

        # Then, try command name (default).
        completions = self._autocomplete_dtsh_cmd(prefix)
        if completions:
            return (DtshAutocomp.MODE_DTSH_CMD, completions)

        return (DtshAutocomp.MODE_ANY, [])

    def _autocomplete_dtsh_cmd(self, prefix: str) -> list[DtshCommand]:
        completions = list[DtshCommand]()
        if prefix.find('/') == -1:
            for cmd in self._dtsh.builtins:
                if (not prefix) or (cmd.name.startswith(prefix) and (len(cmd.name) > len(prefix))):
                    completions.append(cmd)
        return completions

    def _autocomplete_dt_binding(self, prefix: str) -> list[Binding]:
        completions = list[Binding]()
        for compat, binding in self._dtsh.dt_bindings.items():
            if prefix:
                if compat.startswith(prefix) and (len(compat) > len(prefix)):
                    completions.append(binding)
            else:
                completions.append(binding)
        return completions
