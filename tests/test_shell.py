# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Covers the dtsh.shell module."""

import contextlib
import os
import pytest

from devicetree.edtlib import EDT

from dtsh.shell import DevicetreeShell
from dtsh.dtsh import DtshCommandNotFoundError, DtshError, DtshVt


# Context manager pattern borrowed from python-devicetree (test_edtlib.py).
#
HERE = os.path.dirname(__file__)


@contextlib.contextmanager
def from_here():
    cwd = os.getcwd()
    try:
        os.chdir(HERE)
        yield
    finally:
        os.chdir(cwd)


def test_shell_create():
    """Covers DevicetreeShell.create().
    """
    with from_here():
        edt = EDT('test.dts', ['bindings'])
        shell = DevicetreeShell.create('test.dts', ['bindings'])
    assert shell.pwd == edt.get_node('/').path

    with pytest.raises(DtshError):
        shell = DevicetreeShell.create()

    with pytest.raises(DtshError):
        shell = DevicetreeShell.create('invalid.dts', ['bindings'])

    with pytest.raises(DtshError):
        shell = DevicetreeShell.create('test.dts', ['invalid'])


def test_shell_builtins():
    """Covers DevicetreeShell built-ins definition.
    """
    with from_here():
        shell = DevicetreeShell.create('test.dts', ['bindings'])

    assert len(shell.builtins) == 10
    assert shell.builtin('pwd') is not None
    assert shell.builtin('cd') is not None
    assert shell.builtin('ls') is not None
    assert shell.builtin('tree') is not None
    assert shell.builtin('cat') is not None
    assert shell.builtin('alias') is not None
    assert shell.builtin('chosen') is not None
    assert shell.builtin('find') is not None
    assert shell.builtin('uname') is not None
    assert shell.builtin('man') is not None

    with pytest.raises(DtshCommandNotFoundError):
       shell.exec_command_string('unsupported-builtin', DtshVt())
