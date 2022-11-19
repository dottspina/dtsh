# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Covers the dtsh.autocomp module."""

import contextlib
import os

from devicetree.edtlib import EDT

from dtsh.dtsh import DtshAutocomp
from dtsh.autocomp import DevicetreeAutocomp
from dtsh.shell import DevicetreeShell


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


def test_autocomp_empty_cmdline():
    """Covers completion for an empty command line.
    """
    with from_here():
        shell = DevicetreeShell.create('test.dts', ['bindings'])
    completer = DevicetreeAutocomp(shell)

    completions = completer.autocomplete('', '')
    assert len(completions) == len(shell.builtins)


def test_autocomp_command_name():
    """Covers command name completion.
    """
    with from_here():
        shell = DevicetreeShell.create('test.dts', ['bindings'])

    sz_model = len(shell.cwd.children)
    completer = DevicetreeAutocomp(shell)

    # 'ls'
    completions = completer.autocomplete('l', 'l')
    assert len(completions) == 1
    assert completions[0] == 'ls'
    completions = completer.autocomplete('ls', 'ls')
    assert len(completions) == 0
    completions = completer.autocomplete('ls ', '')
    assert len(completions) == sz_model


def test_autocomp_option_name():
    """Covers option name completion.
    """
    with from_here():
        shell = DevicetreeShell.create('test.dts', ['bindings'])
    completer = DevicetreeAutocomp(shell)

    # 'cd [-h --help]'
    completions = completer.autocomplete('cd -', '-')
    assert len(completions) == 1
    completions = completer.autocomplete('cd --', '--')
    assert len(completions) == 1

    # 'ls [-d] [-l] [-r] [-R] [--pager] [-h --help]'
    completions = completer.autocomplete('ls -', '-')
    assert len(completions) == 7
    assert completions[4] == '-f'
    assert completions[5] == '-h'
    assert completions[6] == '--pager'
    completions = completer.autocomplete('ls --', '--')
    assert len(completions) == 2
    assert completions[0] == '--pager'
    assert completions[1] == '--help'


def test_autocomp_nodes():
    """Covers DtshAutocomp.autocomplete_with_nodes()
    """
    with from_here():
        edt = EDT('test.dts', ['bindings'])
        shell = DevicetreeShell.create('test.dts', ['bindings'])

    sz_model = len(edt.get_node('/').children)

    nodes = DtshAutocomp.autocomplete_with_nodes('', shell)
    assert len(nodes) == sz_model

    nodes = DtshAutocomp.autocomplete_with_nodes('/', shell)
    assert len(nodes) == sz_model

    nodes = DtshAutocomp.autocomplete_with_nodes('/*', shell)
    assert len(nodes) == 0

    nodes = DtshAutocomp.autocomplete_with_nodes('paren', shell)
    assert len(nodes) == 1

    nodes = DtshAutocomp.autocomplete_with_nodes('/paren', shell)
    assert len(nodes) == 1

    nodes = DtshAutocomp.autocomplete_with_nodes('parent', shell)
    assert len(nodes) == 0

    nodes = DtshAutocomp.autocomplete_with_nodes('/parent', shell)
    assert len(nodes) == 0

    nodes = DtshAutocomp.autocomplete_with_nodes('/parent/', shell)
    assert len(nodes) == 2

    shell.cd('parent')
    nodes = DtshAutocomp.autocomplete_with_nodes('', shell)
    assert len(nodes) == 2
    nodes = DtshAutocomp.autocomplete_with_nodes('child-', shell)
    assert len(nodes) == 2
    nodes = DtshAutocomp.autocomplete_with_nodes('child_', shell)
    assert len(nodes) == 0
    nodes = DtshAutocomp.autocomplete_with_nodes('child-*', shell)
    assert len(nodes) == 0
