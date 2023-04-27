# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
GNU readline integration.

GNU readline support initialization:
- 1st, try to import the stand-alone GNU readline module
  (`gnureadline`), that should be used on macOS
  to override editline (libedit)
- if failed, try to import the `readline` module from
  the Python standard library, which should be the preferred option
  on systems where the GNU readline shared library is available
- if both failed, abort dtsh (e.g. unlucky MS Windows' users)

See also:
    gnureadline: https://pypi.org/project/gnureadline/
"""

import sys


try:
    import gnureadline as readline  # type: ignore
except ImportError:

    try:
        import readline   # type: ignore
    except ImportError:
        # This version of dtsh won't run without readline support.
        print("dtsh: GNU readline support not found.", file=sys.stderr)
        print("dtsh: Abort.", file=sys.stderr)
        sys.exit(-1)
