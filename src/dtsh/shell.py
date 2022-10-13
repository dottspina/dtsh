# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell PoC implementation."""

from pathlib import Path
import os

from devicetree.edtlib import EDT

from dtsh.cmake import CMakeHelper
from dtsh.dtsh import Dtsh, DtshError
from dtsh.builtin_pwd import DtshBuiltinPwd
from dtsh.builtin_alias import DtshBuiltinAlias
from dtsh.builtin_chosen import DtshBuiltinChosen
from dtsh.builtin_cd import DtshBuiltinCd
from dtsh.builtin_ls import DtshBuiltinLs
from dtsh.builtin_tree import DtshBuiltinTree
from dtsh.builtin_cat import DtshBuiltinCat
from dtsh.builtin_man import DtshBuiltinMan


class DevicetreeShell(Dtsh):
    """Devicetree shell PoC implementation.
    """

    def __init__(self, edt: EDT) -> None:
        """Initialize a devicetree shell with a PoC set of built-in commands.

        Arguments:
        edt -- devicetree model (sources and bindings), provided by edtlib
        """
        super().__init__(edt)
        for cmd in [
                DtshBuiltinPwd(self),
                DtshBuiltinAlias(self),
                DtshBuiltinChosen(self),
                DtshBuiltinCd(self),
                DtshBuiltinLs(self),
                DtshBuiltinTree(self),
                DtshBuiltinCat(self),
                DtshBuiltinMan(self)
                ]:
            self._builtins[cmd.name] = cmd

    @staticmethod
    def create(dt_source_path: str | None = None,
               dt_bindings_path: list[str] | None = None) -> Dtsh:
        """Create a shell-like interface to a devicetree .

        Factory method that loads a devicetree source file and its bindings
        to build a devicetree model (EDT).
        On success, creates a shell-like interface to this devicetree.

        Arguments:
        dt_source_path -- Path to a device tree source file.
                          If unspecified, defaults to '$PWD/build/zephyr/zephyr.dts'
        dt_bindings_path -- List of path to search for DT bindings.
                            If unspecified, and ZEPHYR_BASE is set,
                            defaults to Zephyr's DT bindings.

        Return a new devicetree shell instance.

        Raises DtshError when the devicetree model initialization has failed.
        """
        if not dt_source_path:
            dt_source_path = os.path.join(os.getcwd(),
                                          # Default to current Zephyr project DTS
                                          'build', 'zephyr', 'zephyr.dts')
        if not os.path.isfile(dt_source_path):
            raise DtshError(f"DT source file not found: {dt_source_path}")
        if not dt_bindings_path:
            zephyr_base = os.getenv('ZEPHYR_BASE')
            if zephyr_base:
                dt_bindings_path = DevicetreeShell.get_zephyr_binding_dirs(
                    zephyr_base,
                    dt_source_path
                )
            else:
                raise DtshError('Please provide DT bindings or set ZEPHYR_BASE.')

        try:
            edt = EDT(dt_source_path, dt_bindings_path)
        except Exception as e:
            raise DtshError('Devicetree initialization failed.', e)

        return DevicetreeShell(edt)

    @staticmethod
    def get_zephyr_binding_dirs(zephyr_base: str, dts_path:str) -> list[str]:
        """Answers the list of binding directories Zephyr 'would use'
        at build-time.

        "Where are bindings located ?" specifies that binding files are
        expected to be located in dts/bindings sub-directory of:
        - the zephyr repository
        - the application source directory
        - the board directory
        - any directories in DTS_ROOT
        - any module that defines a dts_root in its build

        Walking through the modules' build settings seems a lot of work
        (needs investigation, and confirmation that it's worth the effort),
        but we should at least try to include:
        - $ZEPHYR_BASE/dts/bindings
        - APPLICATION_SOURCE_DIR/dts/bindings
        - BOARD_DIR/dts/bindings
        - DTS_ROOT/**/dts/bindings

        This implies we get the value of the CMake cached variables
        APPLICATION_SOURCE_DIR, BOARD_DIR and DTS_ROOT.
        To invoke CMake, we'll first need a value for APPLICATION_BINARY_DIR:
        we'll assume its the parent of the directory containing the DTS file,
        as in <app_root>/build/zephyr/zephyr.dts.

        If that fails:
        - APPLICATION_SOURCE_DIR will default to $PWD
        - we will substitute BOARD_DIR/dts/bindings with the ordered
          list [$ZEPHYR_BASE/boards, $PWD/boards]
        - DTS_ROOT: no sensible default

        Only directories that actually exist are included.

        See:
        - $ZEPHYR_BASE/cmake/modules/dts.cmake
        - https://docs.zephyrproject.org/latest/build/dts/bindings.html#where-bindings-are-located

        Arguments:
        zephyr_base -- value of the ZEPHYR_BASE environment variable
        dts_path -- path to the DTS file
        """
        binding_dirs = list[str]()
        dts_dir = os.path.dirname(dts_path)
        app_binary_dir = str(Path(dts_dir).parent.absolute())
        cmake = CMakeHelper(app_binary_dir)

        # $ZEPHYR_BASE/dts/bindings should exist.
        binding_dirs.append(os.path.join(zephyr_base, 'dts', 'bindings'))

        app_src_dir = cmake.getcache('APPLICATION_SOURCE_DIR')
        if not app_src_dir:
            # APPLICATION_SOURCE_DIR will default to $PWD.
            app_src_dir = os.getcwd()
        path = os.path.join(app_src_dir, 'dts', 'bindings')
        if os.path.isdir(path):
            binding_dirs.append(path)

        board_dir = cmake.getcache('BOARD_DIR')
        if board_dir:
            path = os.path.join(board_dir, 'dts', 'bindings')
            if os.path.isdir(path):
                binding_dirs.append(path)
        else:
            # When BOARD_DIR is unset, we add $ZEPHYR_BASE/boards and $PWD/boards,
            # instead of BOARD_DIR/dts/bindings.
            #
            # ISSUE: may we have multiple YAML binding files with the same name,
            # but for different boards (in different directories) ?
            path = os.path.join(os.getcwd(), 'boards')
            if os.path.isdir(path):
                binding_dirs.append(path)
            path = os.path.join(zephyr_base, 'boards')
            if os.path.isdir(path):
                binding_dirs.append(path)

        dts_root = cmake.getcache('DTS_ROOT')
        if dts_root:
            # Append all DTS_ROOT/**/dts/bindings we find.
            for root, _, _ in os.walk(dts_root):
                path = os.path.join(root, 'dts', 'bindings')
                if os.path.isdir(path):
                    binding_dirs.append(path)

        return binding_dirs
