# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'pwd' command."""


from typing import List

from dtsh.dtsh import Dtsh, DtshCommand, DtshVt
from dtsh.dtsh import DtshCommandUsageError


class DtshBuiltinPwd(DtshCommand):
    """Print current working node's path.

DESCRIPTION
The `pwd` command prints the current working node's path.

The current working node's path is also part of the shell multi-line prompt.

EXAMPLES

```
/
❯ pwd
/

/
❯ cd soc

/soc
❯ pwd
/soc

/soc
❯
```
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'pwd',
            "print current working node's path"
        )
        self._dtsh = shell

    def parse_argv(self, argv: List[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)
        if len(self._params) > 0:
            raise DtshCommandUsageError(self, 'too many parameters')

    def execute(self, stdout: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        stdout.write(self._dtsh.pwd)
