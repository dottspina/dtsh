# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Shell-like CLI to a devicetree."""


import sys

from dtsh.dtsh import DtshError
from dtsh.session import DevicetreeShellSession


def run():
    dt_src_path = sys.argv[1] if len(sys.argv) > 1 else None
    dt_bindings_path = sys.argv[2:] if len(sys.argv) > 2 else None

    try:
        DevicetreeShellSession.open(dt_src_path, dt_bindings_path).run()
    except DtshError as e:
        print(f'{str(e)}\n')
        if e.cause:
            print(f'{str(e.cause)}\n')
        # -EINVAL
        sys.exit(-22)


if __name__ == "__main__":
    run()
