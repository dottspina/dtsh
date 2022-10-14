# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Host system tools helpers."""

import os
import re
import sys
from subprocess import Popen, PIPE


class CMakeCache(object):
    """Access CMake cached variables.
    """

    # CMake cached variables name to value.
    _cache: dict[str,str]

    def __init__(self, build_dir: str) -> None:
        """Initialize the CMake helper with a build directory content.

        Will silently fail with an empty cache if the CMake binary is not found,
        or the build directory is invalid.

        Argument:
        build_dir -- path to a valid CMake build directory
        """
        self._cache = dict[str,str]()
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
                self._init_cache(str(stdout, 'utf-8'))
            else:
                # Dump CMake error.
                print(stderr, file=sys.stderr)
        except Exception:
            # Silently fail (cmake is probably unavailable).
            pass

    def get(self, name: str) -> str | None:
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


class Git(object):
    """Git helper.
    """

    def __init__(self) -> None:
        """Initialize helper for host operating system.
        """
        self._git = 'git.exe' if os.name == 'nt' else 'git'

    def get_head_commit(self, repo_path: str) -> str | None:
        """Returns git -C $ZEPHYR_BASE log -n 1 --pretty=format:"%h", or None.
        """
        rev = None
        try:
            argv = [
                self._git,
                '-C', f'{repo_path}',
                'log',
                '-n', '1',
                '--pretty=format:%h'
            ]
            git = Popen(argv, stdout=PIPE, stderr=PIPE)
            stdout, stderr = git.communicate()
            if git.returncode == 0:
                rev = str(stdout, 'utf-8').strip()
            else:
                # Dump git error.
                print(stderr, file=sys.stderr)
        except Exception:
            # Silently fail (git is probably unavailable).
            pass
        return rev

    def get_head_tags(self, repo_path: str) -> list[str]:
        """Returns git tag --points-at HEAD, or None.
        """
        tags = list[str]()
        try:
            argv = [
                self._git,
                '-C', f'{repo_path}',
                'tag',
                '--points-at', 'HEAD',
            ]
            git = Popen(argv, stdout=PIPE, stderr=PIPE)
            stdout, stderr = git.communicate()
            if git.returncode == 0:
                for tag in str(stdout, 'utf-8').splitlines():
                    tags.append(tag.strip())
            else:
                # Dump git error.
                print(stderr, file=sys.stderr)
        except Exception:
            # Silently fail (git is probably unavailable).
            pass
        return tags
