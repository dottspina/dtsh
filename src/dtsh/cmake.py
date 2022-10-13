# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""CMake helper."""

import os
import re
import sys
from subprocess import Popen, PIPE


class CMakeHelper(object):
    """Helper for accessing CMake cached variables.
    """

    # CMake cached ariables name to value.
    _cache: dict[str,str] = dict[str,str]()

    def __init__(self, build_dir: str) -> None:
        """Initialize the CMake helper with a build directory content.

        Will silently fail with an empty cache if the CMake binary is not found,
        or the build directory is invalid.

        Argument:
        build_dir -- path to a valid CMake build directory
        """
        try:
            argv = [
                'cmake.exe' if os.name == 'nt' else 'cmake',
                # List non-advanced cached variables.
                '-L',
                # Only load the cache. Do not actually run configure and generate steps.
                '-N',
                '-B', build_dir
            ]
            cmake = Popen(argv, stdout=PIPE, stderr=PIPE)
            stdout, stderr = cmake.communicate()
            if cmake.returncode == 0:
                self._init_cache(str(stdout, 'UTF-8'))
            else:
                print(stderr, file=sys.stderr)
        except Exception as e:
            print(str(e), file=sys.stderr)

    def getcache(self, name: str) -> str | None:
        """Access CMake cached variables.

        Arguments:
        name -- the variable name, e.g. APPLICATION_SOURCE_DIR

        Returns the variable value or None.
        """
        return self._cache.get(name)

    def _init_cache(self, cmake_stdout: str) -> None:
        regex = re.compile(r'^(\w+):(\w+)=(\S+)$')
        for line in cmake_stdout.splitlines():
            m = regex.match(line)
            if m and (len(m.groups()) == 3):
                self._cache[m.groups()[0]] = m.groups()[2]
