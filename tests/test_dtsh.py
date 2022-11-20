# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Covers the dtsh.dtsh module."""

import contextlib
import os
import pytest

from devicetree.edtlib import EDT

from dtsh.dtsh import Dtsh, DtshUname, DtshCommandOption, DtshCommand, DtshVt
from dtsh.dtsh import DtshError, DtshCommandUsageError, DtshCommandNotFoundError


OPT_LONGFMT = DtshCommandOption('long output format', 'l', None, None)
OPT_VERSION = DtshCommandOption('version', None, 'version', None)
OPT_RECURSE = DtshCommandOption('list recursively', 'R', 'recursive', None)
OPT_REVERSE = DtshCommandOption('reverse order', 'r', 'reverse', None)
OPT_ALIAS   = DtshCommandOption('filter by alias', 'a', None, 'alias')

CMD_LS_OPTIONS = [
    OPT_LONGFMT, OPT_VERSION, OPT_RECURSE, OPT_REVERSE, OPT_ALIAS
]

CMD_LS =  DtshCommand('ls', 'list node contents', True, CMD_LS_OPTIONS)


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


def test_dtsh_nodename():
    """Covers Dtsh.nodename().
    """
    with pytest.raises(ValueError):
        Dtsh.nodename('')

    assert Dtsh.nodename('/') == '/'
    assert Dtsh.nodename('/usr/bin/sort') == 'sort'
    assert Dtsh.nodename('/usr/bin/sort/') == 'sort'
    assert Dtsh.nodename('aliases') == 'aliases'
    assert Dtsh.nodename('/aliases') == 'aliases'
    assert Dtsh.nodename('/dir/glob*') == 'glob*'


def test_dtsh_dirname():
    """Covers Dtsh.dirname().
    """
    with pytest.raises(ValueError):
        Dtsh.dirname('')

    assert Dtsh.dirname('/') == '/'
    assert Dtsh.dirname('/usr/bin') == '/usr'
    assert Dtsh.dirname('/usr/bin/') == '/usr'
    assert Dtsh.dirname('dir1/str') == 'dir1'
    assert Dtsh.dirname('dir1/str/') == 'dir1'
    assert Dtsh.dirname('foobar') == '.'

    # Allows globing.
    assert Dtsh.dirname('dir1/str*') == 'dir1'
    assert Dtsh.dirname('/*') == '/'


def test_dtsh_path_concat():
    """Covers dtsh.Dtsh.path_concat().
    """
    with pytest.raises(ValueError):
        Dtsh.path_concat('', 'dir1')

    assert Dtsh.path_concat('/', 'dir1') == '/dir1'
    assert Dtsh.path_concat('/', 'dir1/') == '/dir1'
    assert Dtsh.path_concat('dir1', 'dir2') == 'dir1/dir2'
    assert Dtsh.path_concat('dir1/', 'dir2') == 'dir1/dir2'
    assert Dtsh.path_concat('/dir1', 'dir2') == '/dir1/dir2'
    assert Dtsh.path_concat('dir1/', 'dir2/') == 'dir1/dir2'

    path = '/dirname/basename'
    assert Dtsh.path_concat(Dtsh.dirname(path), Dtsh.nodename(path)) == path


def test_dtsh_init():
    """Covers Dtsh ctor and properties.
    """
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)
    assert shell.cwd == edt.get_node('/')
    assert shell.pwd == edt.get_node('/').path
    assert len(shell.builtins) == 0
    assert shell.builtin('not-supported') is None


def test_dtsh_realpath():
    """Covers Dtsh.realpath().
    """
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)

    with pytest.raises(ValueError):
        shell.realpath('')

    # The devicetree's root path resolves to '/'.
    assert shell.realpath('/') == '/'

    # A path which starts with '/' resolves to itself but any trailing '/.
    assert shell.realpath('/dir') == '/dir'
    assert shell.realpath('/dir/') == '/dir'

    # Wildcard substitution.
    assert shell.realpath('.') == '/'
    assert shell.realpath('./') == '/'
    assert shell.realpath('./parent') == '/parent'
    # Devicetree's root is its own parent.
    assert shell.realpath('..') == '/'
    assert shell.realpath('../') == '/'
    assert shell.realpath('../parent') == '/parent'

    # Convert to absolute path.
    assert shell.realpath('parent/child-1') == '/parent/child-1'
    shell.cd('/parent/child-2')
    assert shell.realpath('grandchild') == '/parent/child-2/grandchild'

    # Preserve trailing wildcards.
    shell.cd('/')
    assert shell.realpath('*') == '/*'
    assert shell.realpath('/*') == '/*'
    assert shell.realpath('/dir/prefix*') == '/dir/prefix*'

    # Trim trailing slash.
    assert shell.realpath('parent/') == '/parent'


def test_dtsh_path2node():
    """Covers Dtsh.path2node().
    """
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)

    with pytest.raises(ValueError):
        shell.path2node('')

    assert shell.path2node('/') == edt.get_node('/')
    assert shell.path2node('/parent') == edt.get_node('/parent')
    assert shell.path2node('/parent/child-1') == edt.get_node('/parent/child-1')

    with pytest.raises(DtshError):
        shell.path2node('/does-not-exist')

    # path2node() expects an absolute path
    with pytest.raises(DtshError):
        shell.path2node('.')
    with pytest.raises(DtshError):
        shell.path2node('..')
    with pytest.raises(DtshError):
        shell.path2node('parent')


def test_dtsh_cd():
    """Covers `dtsh.Dtsh.cd()`.
    """
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)

    with pytest.raises(ValueError):
        shell.cd('')

    shell.cd('parent')
    assert shell.cwd == edt.get_node('/parent')

    shell.cd('/parent/child-2/grandchild')
    assert shell.cwd == edt.get_node('/parent/child-2/grandchild')

    shell.cd('..')
    assert shell.cwd == edt.get_node('/parent/child-2')
    shell.cd('../')
    assert shell.cwd == edt.get_node('/parent')
    shell.cd('.')
    assert shell.cwd == edt.get_node('/parent')

    shell.cd('../parent/child-1')
    assert shell.cwd == edt.get_node('/parent/child-1')

    shell.cd('/')
    assert shell.cwd == edt.get_node('/')

    with pytest.raises(DtshError):
        shell.cd('/does-not-exist')


def test_dtsh_ls():
    """Covers `dtsh.Dtsh.ls()`.
    """
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)

    with pytest.raises(ValueError):
        shell.ls('')

    nodes = shell.ls('/')
    assert len(nodes) == len(edt.get_node('/').children)

    nodes = shell.ls('parent')
    assert len(nodes) == len(edt.get_node('/parent').children)
    assert nodes[0] == edt.get_node('/parent/child-1')
    assert nodes[1] == edt.get_node('/parent/child-2')

    # Wildcard substitution.
    shell.cd('/parent/child-2')
    nodes = shell.ls('.')
    assert len(nodes) == len(edt.get_node('/parent/child-2').children)
    assert nodes[0] == edt.get_node('/parent/child-2/grandchild')
    nodes = shell.ls('..')
    assert len(nodes) == len(edt.get_node('/parent').children)
    nodes = shell.ls('../child-1')
    assert len(nodes) == len(edt.get_node('/parent/child-1').children)

    # 'ls *' is equivalent to 'ls $pwd'.
    nodes = shell.ls('*')
    assert nodes == shell.ls(shell.pwd)
    assert nodes == [
        edt.get_node('/parent/child-2/grandchild'),
    ]

    # 'ls dirname/*' is equivalent to 'ls dirname'.
    assert shell.ls('/parent/*') == [
        edt.get_node('/parent/child-1'),
        edt.get_node('/parent/child-2'),
    ]

    # 'ls dirname/prefix*' will list the children of the node with path 'dirname'
    # whose name starts with 'prefix'.
    assert shell.ls('/parent/child*') == [
        edt.get_node('/parent/child-1'),
        edt.get_node('/parent/child-2'),
    ]

    # ls('/parent*') is interpreted as ls('/<prefix>*')
    assert shell.ls('/parent*') == [
        edt.get_node('/parent'),
    ]

    # Filtering.
    shell.cd('/parent')
    assert shell.ls('child-*') ==  [
        edt.get_node('/parent/child-1'),
        edt.get_node('/parent/child-2'),
    ]
    nodes = shell.ls('child_*')
    assert len(nodes) == 0

    with pytest.raises(DtshError):
        shell.ls('/does-not-exist')


def test_dtsh_base_exec():
    with from_here():
        sysinfo = DtshUname("test.dts", ["bindings"])
        edt = EDT(sysinfo.dts_path, sysinfo.dt_binding_dirs)
    shell = Dtsh(edt, sysinfo)

    # Ignore empty command strings.
    shell.exec_command_string('', DtshVt())

    with pytest.raises(DtshCommandNotFoundError):
        shell.exec_command_string('ls', DtshVt())


def test_dtsh_command_option():
    """Covers DtshCommandOption.
    """
    assert OPT_REVERSE.shortname == 'r'
    assert OPT_REVERSE.longname == 'reverse'
    assert OPT_REVERSE.argname is None
    assert OPT_REVERSE.usage == '-r --reverse'
    assert OPT_REVERSE.value is None
    assert OPT_REVERSE.is_flag()

    assert OPT_ALIAS.shortname == 'a'
    assert OPT_ALIAS.longname is None
    assert OPT_ALIAS.argname == 'alias'
    assert OPT_ALIAS.usage == '-a <alias>'
    assert OPT_ALIAS.value is None
    assert not OPT_ALIAS.is_flag()

    assert OPT_LONGFMT.shortname == 'l'
    assert OPT_LONGFMT.longname is None
    assert OPT_LONGFMT.argname is None
    assert OPT_LONGFMT.usage == '-l'
    assert OPT_LONGFMT.value is None
    assert OPT_LONGFMT.is_flag()

    OPT_LONGFMT.value = True
    assert OPT_LONGFMT.value == True
    OPT_LONGFMT.reset()
    assert OPT_LONGFMT.value is None


def test_dtsh_command_options():
    """Covers DtshCommand options API.
    """
    # Test pager and help auto-support.
    assert len(CMD_LS.options) == len(CMD_LS_OPTIONS) + 2
    assert CMD_LS.option('--pager') is not None
    assert not CMD_LS.with_flag('--pager')
    assert CMD_LS.option('-h') is not None
    assert not CMD_LS.with_flag('-h')
    # Test custom options
    assert CMD_LS.option('-h') is CMD_LS.option('--help')
    assert CMD_LS.option('-R') is not None
    assert not CMD_LS.with_flag('-R')
    assert CMD_LS.option('--recursive') is not None
    assert not CMD_LS.with_flag('--recursive')
    assert CMD_LS.option('-R') is CMD_LS.option('--recursive')
    assert CMD_LS.option('-r') is not None
    assert not CMD_LS.with_flag('-r')
    assert CMD_LS.option('--reverse') is not None
    assert not CMD_LS.with_flag('--reverse')
    assert CMD_LS.option('-r') is CMD_LS.option('--reverse')

    assert CMD_LS.getopt_short == 'lRra:h'
    assert CMD_LS.getopt_long == ['version', 'recursive', 'reverse', 'pager', 'help']

    argv= [
        '--help',
        '-a',
        'i2c0',
        '-r',
        '--recursive',
        '--version',
        '--pager'
    ]

    with pytest.raises(DtshCommandUsageError):
        # Triggered by the '--help' flag.
        CMD_LS.parse_argv(argv)
    assert CMD_LS.with_flag('-h')
    assert CMD_LS.with_flag('--help')
    assert CMD_LS.with_flag('-r')
    assert CMD_LS.with_flag('--reverse')
    assert CMD_LS.with_flag('-R')
    assert CMD_LS.with_flag('--recursive')
    assert CMD_LS.with_flag('--version')
    assert not CMD_LS.with_flag('-l')
    assert CMD_LS.with_help
    assert CMD_LS.with_pager
    opt_alias = CMD_LS.option('-a')
    assert opt_alias is not None
    assert opt_alias.value is not None

    CMD_LS.reset()
    assert not CMD_LS.with_flag('-h')
    assert not CMD_LS.with_flag('--help')
    assert not CMD_LS.with_flag('-r')
    assert not CMD_LS.with_flag('--reverse')
    assert not CMD_LS.with_flag('-R')
    assert not CMD_LS.with_flag('--recursive')
    assert not CMD_LS.with_flag('--version')
    assert not CMD_LS.with_flag('-l')
    assert not CMD_LS.with_help
    assert not CMD_LS.with_pager
    opt_alias = CMD_LS.option('-a')
    assert opt_alias is not None
    assert opt_alias.value is None

    with pytest.raises(DtshCommandUsageError):
        CMD_LS.parse_argv(['-x'])


def test_dtsh_command_autocomp_option():
    """Covers DtshCommand.autocomplete_option().
    """
    # Prefix does not start with '-', won't match any option.
    completions = CMD_LS.autocomplete_option('')
    assert len(completions) == 0
    completions = CMD_LS.autocomplete_option('x')
    assert len(completions) == 0

    # Prefix '-' should match all options.
    completions = CMD_LS.autocomplete_option('-')
    assert len(completions) == len(CMD_LS_OPTIONS) + 2
    # 1st, all options that have a short name.
    assert completions[0] is OPT_LONGFMT
    assert completions[1] is OPT_RECURSE
    assert completions[2] is OPT_REVERSE
    assert completions[3] is OPT_ALIAS
    assert completions[4].shortname == 'h'
    # Then options that have only a long name.
    assert completions[-2].longname == 'version'
    assert completions[-1].longname == 'pager'

    # Nothing to auto-complete.
    assert len(CMD_LS.autocomplete_option('-h')) == 0

    # Won't complete multiple short options.
    assert len(CMD_LS.autocomplete_option('-ar')) == 0

    assert len(CMD_LS.autocomplete_option('--')) == 5
    assert len(CMD_LS.autocomplete_option('--re')) == 2
    assert len(CMD_LS.autocomplete_option('--rev')) == 1
    assert len(CMD_LS.autocomplete_option('--recursive')) == 0
