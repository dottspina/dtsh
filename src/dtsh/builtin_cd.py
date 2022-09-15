# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'cd' command."""


from typing import Tuple
from dtsh.dtsh import Dtsh, DtshVt, DtshCommand, DtshAutocomp
from dtsh.dtsh import DtshCommandUsageError


class DtshBuiltinCd(DtshCommand):
    """Change current working node.

DESCRIPTION
 The `cd` command changes the shell current working node to `PATH`.

If `PATH` is unspecified, `cd` will change the current working node
to the devicetree's root.

EXAMPLES
```
/
❯ cd /soc/flash-controller@4001e000/

/soc/flash-controller@4001e000
❯ cd

/
❯
```
"""
    def __init__(self, shell: Dtsh) -> None:
        super().__init__(
            'cd',
            'change current working node'
        )
        self._dtsh = shell

    @property
    def usage(self) -> str:
        """Overrides DtshCommand.usage().
        """
        return super().usage + ' [PATH]'

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides Dtsh.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) > 1:
            raise DtshCommandUsageError(self, 'too many parameters')

        if self._params:
            arg_path = self._dtsh.realpath(self._params[0])
        else:
            arg_path = '/'

        self._dtsh.cd(arg_path)

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Overrides DtshCommand.autocomplete_param().
        """
        return (DtshAutocomp.MODE_DT_NODE,
                DtshAutocomp.autocomplete_with_nodes(prefix, self._dtsh))
