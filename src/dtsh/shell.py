# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell PoC implementation."""

import os

from devicetree.edtlib import EDT

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
                dt_bindings_path = [
                    os.path.join(zephyr_base, 'boards'),
                    os.path.join(zephyr_base, 'dts', 'bindings')
                ]
            else:
                raise DtshError('Please provide DT bindings or set ZEPHYR_BASE.')
        for path in dt_bindings_path:
            if not os.path.isdir(path):
                raise DtshError(f"DT bindings directory not found: {path}")

        try:
            edt = EDT(dt_source_path, dt_bindings_path)
        except Exception as e:
            raise DtshError('Devicetree initialization failed.', e)

        return DevicetreeShell(edt)
