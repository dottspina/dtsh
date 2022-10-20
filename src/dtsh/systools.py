# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Host system tools helpers."""


from typing import Any

import os
import re
import sys
import yaml
from pathlib import Path
from subprocess import Popen, PIPE

from devicetree.edtlib import Loader as edtlib_YamlLoader


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


class GCCArm(object):
    """GCC Arm Embedded Toolchain helper.
    """

    # Resolved path to arm-none-eabi-gcc.
    _gcc: str | None

    # Toolchain, e.g.: GNU Arm Embedded Toolchain 10.3-2021.10
    _toolchain: str | None

    # GCC version.
    _version: str | None

    # Build date, e.g. 20210824
    _build_date: str | None

    def __init__(self, gnuarm_dir: str) -> None:
        """Initialize helper for host operating system.
        """
        self._gcc = None
        self._toolchain = None
        self._version = None
        self._build_date = None

        gnuarm_path = Path(os.path.join(gnuarm_dir, 'bin')).resolve()
        if os.path.isdir(gnuarm_path):
            gcc_name = 'arm-none-eabi-gcc.exe' if os.name == "nt" else 'arm-none-eabi-gcc'
            gcc_path = Path(os.path.join(gnuarm_path, gcc_name)).resolve()
            self._gcc = str(gcc_path)
            try:
                argv = [self._gcc, '--version']
                gcc = Popen(argv, stdout=PIPE, stderr=PIPE)
                stdout, stderr = gcc.communicate()
                if gcc.returncode == 0:
                    self._init_version(str(stdout, 'utf-8'))
                else:
                    # Dump gcc error.
                    print(stderr, file=sys.stderr)
            except Exception:
                # Silently fail (gcc is probably unavailable).
                pass

    @property
    def toolchain(self) -> str | None:
        return self._toolchain

    @property
    def version(self) -> str | None:
        return self._version

    @property
    def build_date(self) -> str | None:
        return self._build_date

    def _init_version(self, cmake_stdout: str) -> None:
        # GCC Arm 10:
        # arm-none-eabi-gcc (GNU Arm Embedded Toolchain 10.3-2021.10) 10.3.1 20210824 (release)
        #
        # GCC Arm 11:
        # arm-none-eabi-gcc (GNU Toolchain for the Arm Architecture 11.2-2022.02 (arm-11.14)) 11.2.1 20220111
        regex = re.compile(r'^[\w.\-]+\s([\w .\-()]+)\s([\d.]+)\s(\d+)( [\w()]+)?$')
        for line in cmake_stdout.splitlines():
            m = regex.match(line.strip())
            if m:
                self._toolchain = m.groups()[0]
                self._version = m.groups()[1]
                self._build_date = m.groups()[2]


class GitHub(object):
    """GitHub helper.
    """

    def __init__(self,
                 user: str = "zephyrproject-rtos",
                 project: str = "zephyr") -> None:
        """Initialize helper.

        Arguments:
        user -- GitHub user, defaults to "zephyr-rtos"
        project - GitHub project, defaults to "zephyr"
        """
        self._user = user
        self._project = project

    @property
    def home(self) -> str:
        """Home URL.
        """
        return f"https://github.com/{self._user}/{self._project}"

    def get_tag(self, tag: str):
        """Returns a tag URL.
        """
        return f"{self.home}/releases/tag/{tag}"

    def get_commit(self, commit: str):
        """Returns a commit URL.
        """
        return f"{self.home}/commit/{commit}"


class YamlFile(object):
    """YAML binding file.
    """

    _yaml: Any | None
    _content: str | None

    def __init__(self, path: str):
        """
        """
        yaml_file = None
        try:
            yaml_file = open(path, mode='r', encoding="utf-8")
            self._content = yaml_file.read().strip()
            self._yaml = yaml.load(self._content, edtlib_YamlLoader)
        except IOError:
            self._content = None
            self._yaml = None
        finally:
            if yaml_file:
                yaml_file.close()

    @property
    def content(self) -> str | None:
        """Returns the YAML file content, or None.
        """
        return self._content

    @property
    def include(self) -> list[str]:
        """Returns the list of included YAML files.
        """
        inc_names = list[str]()
        if self._yaml:
            yaml_include = self._yaml.get('include')
            if isinstance(yaml_include, str):
                inc_names.append(yaml_include)
            elif isinstance(yaml_include, list):
                for name in yaml_include:
                    inc_names.append(name)
        return inc_names

    def get(self, key: str) -> Any | None:
        """Access YAML content by key.

        Argument:
        key -- the YAML key
        Returns the mapped content value, or None.
        """
        if self._yaml:
            return self._yaml.get(key)
        return None
