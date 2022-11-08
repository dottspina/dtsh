# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell core API."""


import getopt
import os
import re
from pathlib import Path

from abc import abstractmethod
from typing import ClassVar, Tuple

from devicetree.edtlib import EDT, EDTError, Node, Binding, Property

from dtsh.systools import Git, CMakeCache, GCCArm


class DtshVt(object):
    """Devicetree shells standard I/O API.
    """

    @abstractmethod
    def write(self, *args, **kwargs) -> None:
        """Write (aka print) to stdout.

        Arguments:
        args -- positional arguments for the underlying implementation
        kwargs -- keyword arguments for the underlying implementation
        """

    @abstractmethod
    def pager_enter(self) -> None:
        """Enter pager context.

        Output will be paged until a call to pager_exit().
        """

    @abstractmethod
    def pager_exit(self) -> None:
        """Exit pager context.
        """

    @abstractmethod
    def clear(self) -> None:
        """Clear stdout.
        """

    @abstractmethod
    def readline(self, prompt: str) -> str:
        """Read a line from stdin.

        Will block until ENTER or EOF.

        Arguments:
        prompt -- the prompt to use (see interactive sessions)

        Returns the next line from stdin, with leading and trailing spaces
        striped.

        Raises EOFError when the input stream meets an EOF character.
        """

    @abstractmethod
    def abort(self) -> None:
        """Abort current I/O, since we're either writing to stdout,
        or reading from stdin.
        """


class DtshCommandOption(object):
    """Devicetree shell command option.

    Option definitions are compatible with GNU getopt.

    An option that does not expect any value is a boolean flag.

    An option that expects a named value is an argument.

    An option may admit a short name (e.g. 'v'),
    and/or a long name (e.g. 'verbose').
    """

    _desc: str
    _shortname: str | None
    _longname: str | None
    _arg: str | None
    _value: bool | str | None

    def __init__(self,
                 desc: str,
                 shortname: str | None,
                 longname: str | None,
                 arg: str | None = None) -> None:
        """Define a command option.

        Arguments:
        desc -- short description, e.g. 'use a long listing format'
        shortname -- short option name (e.g. the 'v' in '-v),
                     or None if the option does not admit a short name
        longname -- long option name (e.g. 'verbose' in '--verbose'),
                    or None if the option does not admit a long name
        arg -- the argument name (e.g. in '-a i2c0', the argument name could
               be 'alias'), or None if the option is a flag
        """
        self._desc = desc
        self._shortname = shortname
        self._longname = longname
        self._arg = arg
        self._value = None

    @property
    def desc(self) -> str:
        """The option's description.
        """
        return self._desc

    @property
    def shortname(self) -> str | None:
        """The option's short name, e.g. 'v'.

        This name does not include the '-' prefix,
        neither the ':' postfix when an argument is expected.

        Retutns the option's short name, or None if the option does not admit
        a short name.
        """
        return self._shortname

    @property
    def longname(self) -> str | None:
        """The option's long name, e.g. 'verbose'.

        This name does not include the '--' prefix,
        neither the '=' postfix when an argument is expected.

        Returns the option's long name, or None if the option does not admit
        a long name.
        """
        return self._longname

    @property
    def argname(self) -> str | None:
        """The option's argument name, or None if the options is a flag.
        """
        return self._arg

    @property
    def usage(self) -> str:
        """The option's usage string, e.g. '-a <alias> -v --verbose'.
        """
        txt = ''
        if self._shortname:
            txt = f"-{self._shortname}"
        if self._longname:
            if txt:
                txt += f" --{self._longname}"
            else:
                txt = f"--{self._longname}"
        if self._arg:
            txt += f" <{self._arg}>"
        return txt

    @property
    def value(self) -> bool | str | None:
        """The option's value.

        Before a command's options are parsed, this value is None.

        After the command string is successfully parsed, an option value is:
        - True (set) or False (unset) for a flag
        - a string value for an argument
        """
        return self._value

    @value.setter
    def value(self, v: bool | str):
        """Set the option's value.

        The options values are typically set when parsing a command string.

        Arguments:
        v -- True (False) to set (unset) a flag,
             or a string value to set an argument
        """
        self._value = v


    def is_flag(self) -> bool:
        """Returns True if the option does not expect any value.
        """
        return self._arg is None

    def reset(self):
        """Reset this option's value, typically before parsing a command string.
        """
        self._value = None


class DtshCommand(object):
    """Devicetree shell command.
    """

    # Name, e.g. 'ls'.
    _name: str
    # Description, e.g. 'list nodes content'.
    _desc: str
    # Supported options.
    _options: list[DtshCommandOption]
    # Parsed parameters (command string components that are not parsed options).
    _params: list[str]

    def __init__(self,
                 name: str,
                 desc: str,
                 with_pager: bool = False,
                 options: list[DtshCommandOption] = []) -> None:
        """Defines a devicetree shell command.

        Arguments:
        name -- the command's name (e.g. 'ls')
        desc -- the command's description
        with_pager -- if True, enables pager option support
        options -- the command's options
        """
        self._name = name
        self._desc= desc
        self._params = list[str]()
        self._options = list[DtshCommandOption]()
        self._options.extend(options)
        if with_pager:
            self._options.append(
                DtshCommandOption('page command output', None, 'pager', None)
            )
        self._options.append(
            DtshCommandOption('print usage summary', 'h', 'help', None)
        )

    @property
    def name(self) -> str:
        """Command's name, e.g. 'ls'.
        """
        return self._name

    @property
    def desc(self) -> str:
        """Command's description, e.g. 'list nodes content'.
        """
        return self._desc

    @property
    def usage(self) -> str:
        """The command's usage string, '<cmd> [options]'.
        """
        txt = self._name
        for opt in self._options:
            txt += f" [{opt.usage}]"
        return txt

    @property
    def options(self) -> list[DtshCommandOption]:
        """Available options.
        """
        return self._options

    @property
    def getopt_short(self) -> str:
        """Short options specification string compatible with GNU getopt.

        e.g. 'ha:' when the option supports a flag '-h',
        and an argument '-a:'.
        """
        shortopts = ''
        for opt in self._options:
            if opt.shortname:
                shortopts += opt.shortname
                if opt.argname:
                    shortopts += ':'
        return shortopts

    @property
    def getopt_long(self) -> list[str]:
        """Long options specification list compatible with GNU getopt.

        e.g. ['help','alias='] when the option supports a flag '--help',
        and an argument '--alias='.
        """
        longopts = []
        for opt in self._options:
            if opt.longname:
                longopt = opt.longname
                if opt.argname:
                    longopt += '='
                longopts.append(longopt)
        return longopts

    @property
    def with_pager(self) -> bool:
        return self.with_flag('--pager')

    @property
    def with_usage_summary(self) -> bool:
        return self.with_flag('-h')

    def option(self, name: str) -> DtshCommandOption | None:
        """Access a supported option.

        Arguments:
        name -- an option's name, either a short form (e.g. '-h'),
                or a long form (e.g. '--help')

        Returns None if the option is not supported by this command.
        """
        for opt in self._options:
            if name.startswith('--') and opt.longname:
                if name[2:] == opt.longname:
                    return opt
            elif name.startswith('-') and opt.shortname:
                if name[1:] == opt.shortname:
                    return opt
        return None

    def with_flag(self, name: str) -> bool:
        """Access a command's flag.

        Arguments:
        name -- the flag's name, either a short form (e.g. '-v'),
                or a long form (e.g. '--verbose')

        Returns True if name refers to a set flag, False otherwise.
        """
        opt = self.option(name)
        if opt:
            return opt.is_flag() and (opt.value == True)
        return False

    def arg_value(self, name) -> str | None:
        """Access an argument value.

        Arguments:
        name -- the option name

        Returns the argument value, None if the option was not provided on
        the command line, or if the option is a flag.
        """
        opt = self.option(name)
        # Note that parse_argv() would have failed if the argument
        # if actually defined as an argument (parse error otherwise).
        if opt and (not opt.is_flag()) and (opt.value is not None):
            return str(opt.value)
        return None

    def reset(self) -> None:
        """Reset command options and parameters.
        """
        for opt in self._options:
            opt.reset()
        self._params.clear()

    def parse_argv(self, argv: list[str]) -> None:
        """Parse command line arguments, setting options and parameters.

        Arguments:
        argv -- the command's arguments

        Raises DtshCommandUsageError when the arguments do not match the
        command's usage (getopt).
        """
        self.reset()
        try:
            parsed_opts, self._params = getopt.gnu_getopt(argv,
                                                          self.getopt_short,
                                                          self.getopt_long)
        except getopt.GetoptError as e:
            raise DtshCommandUsageError(self, str(e), e)

        for opt_name, opt_arg in parsed_opts:
            opt = self.option(opt_name)
            if opt:
                if opt.argname:
                    opt.value = opt_arg
                else:
                    opt.value = True

    def autocomplete_option(self, prefix: str) -> list[DtshCommandOption]:
        """Auto-complete a command's options name.

        Arguments:
        prefix -- the option's name prefix, starting with '-' or '--'

        Returns a list of matching options.
        """
        completions = list[DtshCommandOption]()

        if prefix == '-':
            # Match all options, sorting with short names first.
            shortopts = [o for o in self._options if o.shortname]
            completions.extend(shortopts)
            # Then options with long names only.
            otheropts = [
                o for o in self._options if o.longname and (o not in shortopts)
            ]
            completions.extend(otheropts)

        elif prefix.startswith('--'):
            # Auto-comp long option names only.
            p = prefix[2:]
            for opt in self._options:
                if not opt.longname:
                    continue
                if not p:
                    completions.append(opt)
                    continue
                if opt.longname.startswith(p) and (len(opt.longname) > len(p)):
                    completions.append(opt)

        return completions

    def autocomplete_argument(self,
                              arg: DtshCommandOption,
                              prefix: str) -> list[str]:
        """Auto-complete a command's option value (aka argument).

        Arguments:
        arg -- the option expecting a value
        prefix -- the option's name prefix, starting with '-' or '--'

        Returns a list of matching arguments.
        """
        return []

    def autocomplete_param(self, prefix: str) -> Tuple[int,list]:
        """Auto-complete a command's parameter value.

        Completions are represented by the tagged list of possible
        parameter objects.

        The tag will help client code to interpret (type) these parameter values.

        Arguments:
        prefix -- the startswith pattern for parameter values

        Returns the tagged list of matching parameters as a tuple.
        """
        return DtshAutocomp.MODE_ANY, []

    @abstractmethod
    def execute(self, vt: DtshVt) -> None:
        """Execute the shell command.

        Arguments:
        vt -- where the command will write its output

        Raises DtshError when the command execution has failed.
        """


class DtshUname(object):
    """System information inferred from environment variables,
    CMake cached variables and Zephyr's Git repository state.

    All paths are resolved (absolute, resolving any symlinks,
    “..” components are also eliminated).
    """

    # Resolved DTS file path.
    _dts_path: str

    # Resolved binding directories.
    _binding_dirs: list[str]

    # Resolved $ZEPHYR_BASE.
    _zephyr_base: str | None

    # Resolved $ZEPHYR_SDK_INSTALL_DIR.
    _zephyr_sdk_dir: str | None

    # Cached $ZEPHYR_SDK_INSTALL_DIR/sdk_version file content.
    _zephyr_sdk_version: str | None

    # Resolved $GNUARMEMB_TOOLCHAIN_PATH.
    _gnuarm_dir: str | None

    # $ZEPHYR_TOOLCHAIN_VARIANT ('gnuarmemb' or 'zephyr').
    _zephyr_toolchain: str | None

    # git -C $ZEPHYR_BASE log -n 1 --pretty=format:"%h"
    _zephyr_rev: str | None

    # git tag --points-at HEAD
    _zephyr_tags: list[str]

    # Resolved BOARD_DIR (CMake).
    _board_dir: str | None

    # CMake cached variables.
    _cmake_cache: CMakeCache

    def __init__(self, dts_path:str, binding_dirs: list[str] | None) -> None:
        """Initialize system info.

        Arguments:
        dts_path -- Path to a devicetree source file.
        binding_dirs -- List of path to search for DT bindings.
                        If unspecified, and ZEPHYR_BASE is set,
                        defaults to Zephyr's DT bindings.

        Raises DtshError when a specified path is invalid.
        """
        try:
            self._dts_path = str(Path(dts_path).resolve(strict=True))
        except FileNotFoundError as e:
            raise DtshError(f"DTS file not found: {dts_path}", e)

        self._binding_dirs = list[str]()
        self._zephyr_tags = list[str]()
        self._zephyr_base = None
        self._zephyr_sdk_dir = None
        self._zephyr_sdk_version = None
        self._gnuarm_dir = None
        self._zephyr_toolchain = None
        self._zephyr_rev = None
        self._board_dir = None

        self._load_environment()
        self._load_cmake_cache()

        if self._zephyr_base:
            git = Git()
            self._zephyr_rev = git.get_head_commit(self._zephyr_base)
            self._zephyr_tags = git.get_head_tags(self._zephyr_base)

        if binding_dirs:
            for binding_dir in binding_dirs:
                path = Path(binding_dir).resolve()
                if os.path.isdir(path):
                    self._binding_dirs.append(str(path))
                else:
                    raise DtshError(f"Bindings directory not found: {binding_dir}")
        elif self._zephyr_base:
            self._init_zephyr_bindings_search_path()

    @property
    def dts_path(self) -> str:
        """Returns the resolved path to the session's DT source file.
        """
        return self._dts_path

    @property
    def dt_binding_dirs(self) -> list[str]:
        """Returns the DT bindings search path as a list of resolved path.

        When no bindings are specified by the dtsh command line,
        and the environment variable ZEPHYR_BASE is set,
        we'll try to default to the bindings Zephyr would use (has used)
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
        but we'll at least try to include:
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
        - we will substitute BOARD_DIR/dts/bindings with $ZEPHYR_BASE/boards
          and $PWD/boards (we don't know if it's a Zephyr board or a custom board,
          we don't know wich <arch>/<board>/dts/bindings subdirectory to select)

        Only directories that actually exist are included.

        See:
        - $ZEPHYR_BASE/cmake/modules/dts.cmake
        - https://docs.zephyrproject.org/latest/build/dts/bindings.html#where-bindings-are-located
        """
        return self._binding_dirs

    @property
    def zephyr_base(self) -> str | None:
        """Returns the resolved path to the Zephyr kernel repository set by
        the environment variable ZEPHYR_BASE, or None if unset.
        """
        return self._zephyr_base

    @property
    def zephyr_toolchain(self) -> str | None:
        """Returns the toolchain variant ('zephyr' or 'gnuarmemb') set by the
        environment variable ZEPHYR_TOOLCHAIN_VARIANT, or None if unset.
        """
        return self._zephyr_toolchain

    @property
    def zephyr_sdk_dir(self) -> str | None:
        """Returns resolved path the Zephyr SDK directory set by the environment
        variable ZEPHYR_SDK_INSTALL_DIR, or None if unset.
        """
        return self._zephyr_sdk_dir

    @property
    def gnuarm_dir(self) -> str | None:
        """Value of the environment variable GNUARMEMB_TOOLCHAIN_PATH, or None.
        """
        """Returns the GCC Arm base directory set by the environment variable
        GNUARMEMB_TOOLCHAIN_PATH, or None if unset.
        """
        return self._gnuarm_dir

    @property
    def zephyr_kernel_rev(self) -> str | None:
        """Returns the Zephyr kernel revision as given by
        git -C $ZEPHYR_BASE log -n 1 --pretty=format:"%h",
        or None when unavailable.
        """
        return self._zephyr_rev

    @property
    def zephyr_kernel_tags(self) -> list[str]:
        """Returns the Zephyr kernel tags for the current
        repository state, as given by git tag --points-at HEAD,
        or None when unavailable.
        """
        return self._zephyr_tags

    @property
    def zephyr_kernel_version(self) -> str | None:
        """Returns the Zephyr kernel version tag for the current
        repository state, e.g. 'zephyr-v3.1.0',
        or None if the state does not match a tagged Zephyr kernel release.
        """
        version = None
        if self.zephyr_kernel_tags:
            # Include stable and RC releases.
            regex = re.compile(r'^zephyr-(v\d.\d.\d[rc\-\d]*)$')
            for tag in self.zephyr_kernel_tags:
                m = regex.match(tag)
                if m:
                    version = tag
                    break
        return version

    @property
    def zephyr_sdk_version(self) -> str | None:
        """Returns the Zephyr SDK version set in the file
        $ZEPHYR_SDK_INSTALL_DIR/sdk_version, or None if unavailable.
        """
        if self._zephyr_sdk_version is None:
            if self._zephyr_sdk_dir:
                path = os.path.join(self._zephyr_sdk_dir, 'sdk_version')
                try:
                    with open(path, 'r') as f:
                        self._zephyr_sdk_version = f.read().strip()
                except IOError:
                    # Silently fail.
                    pass
        return self._zephyr_sdk_version

    @property
    def gnuarm_version(self) -> str | None:
        """Returns GCC Arm toolchain version, or None if unavailable.
        """
        if self._gnuarm_dir:
            return GCCArm(self._gnuarm_dir).version
        return None

    @property
    def board_dir(self) -> str | None:
        """Returns the resolved path to the board directory set by
        the CMake cached variable BOARD_DIR, or None if unavailable.
        """
        return self._board_dir

    @property
    def board(self) -> str | None:
        """Returns the best guess fo the board (try BOARD environment variable
        and CMake cache) or None if unavailable.
        """
        # 1st, try environmant variable.
        found_board = os.getenv('BOARD')
        if not found_board:
            # Then try CMake cache.
            found_board = self._cmake_cache.get('BOARD')
            if not found_board:
                # More likely than above.
                found_board = self._cmake_cache.get('CACHED_BOARD')
                if (not found_board) and self.board_dir:
                    # Fallback: extract BOARD from BOARD_DIR
                    found_board = os.path.basename(self.board_dir)
        return found_board

    @property
    def board_dts_file(self) -> str | None:
        """Returns the best guess for the the DTS file path (relies on
        CMake cache), or None if unavailable.
        """
        if self.board_dir and self.board:
            path = os.path.join(self.board_dir, f'{self.board}.dts')
            if os.path.isfile(path):
                return path
        return None

    @property
    def board_binding_file(self) -> str | None:
        """Returns the best guess for the board binding file path (relies on
        CMake cache), or None if unavailable.
        """
        if self.board_dir and self.board:
            path = os.path.join(self.board_dir, f'{self.board}.yaml')
            if os.path.isfile(path):
                return path
        return None

    def _load_environment(self) -> None:
        env = os.getenv('ZEPHYR_BASE')
        if env:
            path = Path(env).resolve()
            self._zephyr_base = str(path)
        env = os.getenv('ZEPHYR_SDK_INSTALL_DIR')
        if env:
            path = Path(env).resolve()
            self._zephyr_sdk_dir = str(path)
        env = os.getenv('GNUARMEMB_TOOLCHAIN_PATH')
        if env:
            path = Path(env).resolve()
            self._gnuarm_dir = str(path)
        self._zephyr_toolchain = os.getenv('ZEPHYR_TOOLCHAIN_VARIANT')

    def _load_cmake_cache(self) -> None:
        # self._dts_path is already resolved.
        dts_dir = os.path.dirname(self._dts_path)
        if os.path.isdir(dts_dir):
            build_dir = str(Path(dts_dir).parent.absolute())
            self._cmake_cache = CMakeCache(build_dir)

    def _init_zephyr_bindings_search_path(self) -> None:
        if not self._zephyr_base:
            return
        # self._zephyr_base is already resolved.
        path = Path(os.path.join(self._zephyr_base, 'dts', 'bindings'))
        self._binding_dirs.append(str(path))

        app_src_dir = self._cmake_cache.get('APPLICATION_SOURCE_DIR')
        if not app_src_dir:
            # APPLICATION_SOURCE_DIR will default to $PWD.
            app_src_dir = os.getcwd()
        path = Path(os.path.join(app_src_dir, 'dts', 'bindings')).resolve()
        if os.path.isdir(path):
            self._binding_dirs.append(str(path))

        board_dir = self._cmake_cache.get('BOARD_DIR')
        if board_dir:
            board_path = Path(board_dir).resolve()
            self._board_dir = str(board_path)
            binding_path = Path(os.path.join(board_dir, 'dts', 'bindings')).resolve()
            if os.path.isdir(binding_path):
                self._binding_dirs.append(str(binding_path))
        else:
            # When BOARD_DIR is unset, we add both $ZEPHYR_BASE/boards
            # and $PWD/boards (we don't know if it's a Zephyr board
            # or a custom board).
            #
            # ISSUE: may we have multiple YAML binding files with the same name,
            # but for different boards (in different directories) ?
            path = Path(os.path.join(self._zephyr_base, 'boards')).resolve()
            if os.path.isdir(path):
                self._binding_dirs.append(str(path))
            path = Path(os.path.join(os.getcwd(), 'boards')).resolve()
            if os.path.isdir(path):
                self._binding_dirs.append(str(path))

        dts_root = self._cmake_cache.get('DTS_ROOT')
        if dts_root:
            # Append all DTS_ROOT/**/dts/bindings we find.
            for root, _, _ in os.walk(dts_root):
                path = Path(os.path.join(root, 'dts', 'bindings')).resolve()
                if os.path.isdir(path):
                    self._binding_dirs.append(str(path))


class Dtsh(object):
    """Shell-like interface to a devicetree.

    The global metaphor is:
    - a filesystem-like view of the devicetree model
    - a command string interface to POSIX-like shell commands (aka built-ins)
    """

    API_VERSION = '0.1.0a4'
    """API version for the dtsh module.

    Should match 'version' in setup.py.
    """

    # Devicetree model (edtlib).
    _edt: EDT

    # Current working node.
    _cwd: Node

    # Built-in commands.
    _builtins: dict[str, DtshCommand]

    # Cached bindings map.
    _bindings: dict[str, Binding]

    # Cached available DT binding paths (including YAML files that do
    # not describe a compatible).
    # Memory trade-off: this map may contain about 2000 entries.
    _binding2path: dict[str, str]

    # Sysinfo.
    _uname: DtshUname

    def __init__(self, edt: EDT, uname: DtshUname) -> None:
        """Initialize a shell-like interface to a devicetree.

        The current working node is initialized to the devicetree's root.

        The built-in list is empty.

        Arguments:
        edt -- devicetree model (sources and bindings), provided by edtlib
        uname -- system information inferred from environment variables,
                 CMake cached variables, Zephyr's Git repository state.
        """
        self._edt = edt
        self._uname = uname
        self._cwd = self._edt.get_node('/')
        self._builtins = dict[str, DtshCommand]()
        self._bindings = dict[str, Binding]()
        self._binding2path = dict[str, str]()
        self._init_binding_paths()
        self._init_bindings()

    @property
    def uname(self) -> DtshUname:
        """System information inferred from environment variables,
        CMake cached variables and Zephyr's Git repository state.

        This is the system information used to initialize the
        devicetree and its bindings.
        """
        return self._uname

    @property
    def cwd(self) -> Node:
        """Current working node.
        """
        return self._cwd

    @property
    def pwd(self) -> str:
        """Current working node's path.
        """
        return self._cwd.path

    @property
    def builtins(self) -> list[DtshCommand]:
        """Available shell built-ins as a list.
        """
        return [cmd for _, cmd in self._builtins.items()]

    @property
    def dt_bindings(self) -> dict[str, Binding]:
        """Map each compatible to its binding.

        This collection should include all compatibles that are both:
        - matched (by a node's "compatible" property)
        - described (by a corresponding YAML file)

        However, the current implementation of the devicetree model initialization
        may filter out bindings that never appear first (i.e. as most specific)
        in the "compatible" list of a node.
        For example, the binding for "nordic,nrf-swi" is likely to
        always be masked by a more specific compatible, e.g. "nordic,nrf-egu".
        """
        return self._bindings

    def dt_binding(self, compat: str) -> Binding | None:
        """Access bindings by their compatible.

        See Dtsh.dt_bindings() for limitations.

        Arguments:
        compat -- a compatible (DTSpec 2.3.1)

        Returns the binding describing this compatible,
        or None when this compatible is either unmatched or not described.
        """
        return self._bindings.get(compat)

    def dt_binding_path(self, fname: str) -> str | None:
        """Search binding directories for a given DT specification file name.

        Contrary to the Dtsh.dt_binding() API, this search is not limited
        to bindings that describe a compatible.

        Arguments
        fname -- the YAML file name, e.g. "nordic,nrf-swi.yaml"

        Returns the full path of the YAML file, or None when not found.
        """
        return self._binding2path.get(fname)

    @property
    def dt_aliases(self) -> dict[str, Node]:
        aliases = dict[str, Node]()
        for alias, dt_node in self._edt._dt.alias2node.items():
            edt_node = self._edt.get_node(dt_node.path)
            aliases[alias] = edt_node
        return aliases

    @property
    def dt_chosen(self) -> dict[str, Node]:
        return self._edt.chosen_nodes

    def builtin(self, name: str) -> DtshCommand | None:
        """Access a built-in by command name.

        Arguments:
        name -- a command name

        Returns None if this  built-in name is not supported by this command.
        """
        return self._builtins.get(name)

    def realpath(self, path: str) -> str:
        """Resolve a node's path.

        The devicetree's root path resolves to '/'.

        An absolute path resolves to itself.

        When the path starts with '.', wildcard substitution occurs:
        - a leading '.' represents the current working node
        - a leading '..' represents the current working node's parent;
          the devicetree's root is its own parent

        Otherwise, path is concatenated to the current working node's path.

        Path resolution will always:
        - strip any trailing '/' (excepted for the devicetree's root)
        - preserve any trailing wildcard ('*')

        See also: man realpath(1), but here none of the path components
        is required to exist (i.e. to actually represent a devicetree node).

        Arguments:
        path -- the node's path to resolve

        Returns the resolved path.

        Raises ValueError when path is unspecified.
        """
        if not path:
            raise ValueError('path must be specified')

        if path.startswith('/'):
            # The devicetree's root path resolves to '/'.
            # A path which starts with '/' resolves to itself but any trailing '/.
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]
        else:
            if path.startswith('.'):
                # Wildcard substitution.
                if path.startswith('..'):
                    dirpath = Dtsh.dirname(self.pwd)
                    path_trailing = path[2:]
                else:
                    dirpath = self.pwd
                    path_trailing = path[1:]
                # Handle '../dir' and './dir' (typical case).
                if path_trailing.startswith('/'):
                    path_trailing = path_trailing[1:]

                if path_trailing:
                    path = Dtsh.path_concat(dirpath, path_trailing)
                else:
                    path = dirpath
            else:
                # Otherwise, path is concatenated to the current
                # working node's path.
                path = Dtsh.path_concat(self.pwd, path)

        return path

    def path2node(self, path:str) -> Node:
        """Access devicetree nodes by path.

        Arguments:
        path -- an absolute devicetree node's path

        Returns a devicetree node (EDT).

        Raises:
        - ValueError when path is unspecified
        - DtshError when path does not represent an actual devicetree node
        """
        if not path:
            raise ValueError('path must be specified')

        try:
            return self._edt.get_node(path)
        except EDTError as e:
            raise DtshError(f'no such node: {path}', e)

    def isnode(self, path: str) -> bool:
        """Answsers whether a path represents an actual devicetree node.

        Arguments:
        path -- an absolute devicetree node's path

        Raises:
        - ValueError when path is unspecified
        """
        try:
            self._edt.get_node(path)
            return True
        except EDTError:
            pass
        return False

    def cd(self, path: str) -> None:
        """Change the current working node.

        The path is first resolved (see `Dtsh.realpath()`).

        Arguments:
        path -- a node's path, either absolute or relative

        Raises:
        - ValueError when path is unspecified
        - DtshError when the destination node does not exist
        """
        path = self.realpath(path)
        self._cwd = self.path2node(path)

    def ls(self, path: str) -> list[Node]:
        """List a devicetree node's children.

        The path is first resolved (see `Dtsh.realpath()`) to:

           <directory>[<filter>]

           <filter> := [/][<prefix>]'*'

        Filtering is thereby applied if the resolved path ends
        with a trailing '*', such that:

           ls('<directory>/[<prefix>]*')

        will list the children of the node with path '<directory>',
        whose name starts with prefix '<prefix>'.

        When 'prefix' is not set,

           ls('<directory>/*')

        is equivalent to:

           ls('<directory>')

        Note that

           ls('/parent*')

        is interpreted as

           ls('/<prefix>*')

        with '<prefix>' equals to 'parent', even if '/parent' is the path
        to an actual devicetree node.

        Arguments:
        path -- a node's path, either absolute or relative

        Returns the listed nodes.

        Raises:
        - ValueError when path is unspecified
        - DtshError on devicetree node path's resolution failure
        """
        path = self.realpath(path)

        if path.endswith('*'):
            dirpath = Dtsh.dirname(path)
            prefix = path[:-1]
            return [n for n in self.ls(dirpath) if n.path.startswith(prefix)]
        else:
            dirnode = self.path2node(path)
            return list[Node](dirnode.children.values())

    def exec_command_string(self, cmd_str: str, vt: DtshVt) -> None:
        """Execute a command string.

        Note that the command string content after any '--' token
        will be interpreted as command parameters.

        See:
        - https://docs.python.org/3.9/library/getopt.html

        Arguments:
        cmd_str -- the command string in GNU getopt format
        vt -- where the command will write its output,
              or None for quiet execution

        Raises:
        - DtshCommandNotFoundError when the requested command is not supported
        - DtshCommandUsageError when the command string does not match
          the associated GNU getopt usage
        - DtshCommandFailedError when the command execution has failed
        """
        if not cmd_str:
            return

        cmdline_vstr = cmd_str.strip().split()
        cmd_name = cmdline_vstr[0]

        cmd = self._builtins.get(cmd_name)
        if not cmd:
            raise DtshCommandNotFoundError(cmd_name)

        # Set command options and parameters (raises DtshCommandUsageError).
        cmd_argv = cmdline_vstr[1:]
        cmd.parse_argv(cmd_argv)

        try:
            cmd.execute(vt)
        except DtshError as e:
            raise DtshCommandFailedError(cmd, e.msg, e)

    @staticmethod
    def is_node_enabled(node: Node):
        """Returns True if the node is enabled according to its status.
        """
        return node.status in ['ok', 'okay']

    @staticmethod
    def nodename(path: str) -> str:
        """Strip directory and suffix ('/') components from a node's path.

        See also: man basename(1)

        Arguments:
        path -- a node's path, either absolute or relative

        Returns path with any leading directory components removed.

        Raises ValueError when path is unspecified.
        """
        if not path:
            raise ValueError('path must be specified')

        if path == '/':
            return '/'

        x = path.rfind('/')
        if x < 0:
            return path

        if path.endswith('/'):
            path = path[:-1]
            x = path.rfind('/')

        return path[x+1:]

    @staticmethod
    def dirname(path: str) -> str:
        """Strip last component from a node's name.

        See also: man dirname(1)

        Arguments:
        path -- a node's path, either absolute or relative

        Returns path with its last non-slash component and trailing slashes removed,
        or '.' when path does not contain any '/'.

        Raises ValueError when path is unspecified.
        """
        if not path:
            raise ValueError('path must be specified')

        x = path.rfind('/')
        if x == 0:
            # dirname('/[<postfix>]') = '/'
            return '/'
        if x > 0:
            # dirname('<prefix>/[<postfix>]') = '<prefix>'
            if path.endswith('/'):
                x = path.rfind('/', 0, len(path) - 1)
            return path[0:x]

        # Path does not contain any '/'.
        return '.'

    @staticmethod
    def path_concat(path_prefix: str, path: str) -> str:
        """Devicetree node path concatenation.

        This helper will:
        - assert path is relative (does not start with '/')
        - append '/' to path_prefix when appropriate
        - drop any trailing '/' from path

        Arguments:
        path_prefix -- the leading path prefix
        path -- the relative path to concatenate

        Returns the resulting path.

        Raises ValueError when path_prefix or path is unspecified,
        or when path starts with '/'.
        """
        if not path_prefix:
            raise ValueError('path prefix must specified')
        if not path:
            raise ValueError('path must specified')
        if path.startswith('/'):
            raise ValueError('path must be relative')

        if not path_prefix.endswith('/'):
            path_prefix += '/'
        if path.endswith('/'):
            path = path[:-1]

        return path_prefix + path

    @staticmethod
    def cfg_dir_path() -> str:
        xdg_cfg_dir = os.environ.get('XDG_CONFIG_HOME')
        if not xdg_cfg_dir:
            home = os.path.expanduser('~')
            xdg_cfg_dir = os.path.join(home, '.config')
        return os.path.join(xdg_cfg_dir, 'dtsh')

    def _init_bindings(self) -> None:
        # EDT.compat2nodes includes all compatibles matched by a devicetree node.
        # See also EDT._init_luts().
        for compat, nodes in self._edt.compat2nodes.items():
            # A compatible may not map to any binding in the devicetree
            # underlying model:
            # - a compatible that represents a board, for which the binding
            #   is looked up with the board identifier, and describes the board
            #   itself (e.g. architecture, supported toolchains and Zephyr subsystems)
            #   and not a devicetree content; for example, the board identified
            #   by "nrf52840dk_nrf52840" is described by its binding file nrf52840dk_nrf52840.yaml,
            #   while its DTS file nrf52840dk_nrf52840.dts will set the
            #   compatible property of the devicetree root node to "nordic,nrf52840-dk-nrf52840"
            # - a compatible somewhat part of the DT core specifications
            #   (e.g. "simple-bus", DTSpec 4.5)
            # - a compatible that does not define any property beside those
            #   inherited from the base bindings (e.g. "arm,armv7m-systick")
            # - typically a compatible that isn't described by any YAML file
            #
            # See also edtlib.Binding.compatible:
            # For example, it's None when the Binding is inferred
            # from node properties. It can also be None for Binding objects
            # created using 'child-binding:' with no compatible.
            binding = None
            for node in nodes:
                # There are handfull of issues here:
                # - we access the private member edtlib.Node._binding,
                #   and assume Node.matching_compat will equal to
                #   Node._binding.compatible wherever a node has a binding
                # - filtering by Node.matching_compat may filter out
                #   compatibles that are actually matched by devicetree nodes;
                #   e.g. the compatible "nordic,nrf-swi" that's matched by
                #   nodes with the more specific compatible "nordic,nrf-egu"
                #   will remain undefined despite the proper binding file
                #   (nordic,nrf-swi.yaml) being available
                # - not filtering on Node.matching_compat would /define/
                #   inconsistent bindings, e.g. the compatible "nordic,nrf-swi"
                #   would bind with nordic,nrf-egu.yaml
                #
                # See also edtlib.EDT._init_compat2binding()
                if node._binding and (node.matching_compat == compat):
                    binding = node._binding
                    break
            if not binding:
                # We may have missed a binding for a compatible that never
                # appears as the most specific (see above): if a corresponding
                # YAML file seems to actually exist, try to instantiate an
                # out-of-devicetree Binding.
                path = self.dt_binding_path(f'{compat}.yaml')
                if path:
                    # WARNING: this may fail with an exception,
                    # for now let it crash to better know how and when.
                    binding = Binding(path, self._binding2path)
            if binding:
                self._bindings[compat] = binding

    def _init_binding_paths(self) -> None:
        # Mostly duplicates code from edtlib._binding_paths()
        # and edtlib.EDT._init_compat2binding().
        yaml_paths = list[str]()
        for bindings_dir in self._edt.bindings_dirs:
            for root, _, filenames in os.walk(bindings_dir):
                for filename in filenames:
                    if filename.endswith(".yaml") or filename.endswith(".yml"):
                        yaml_paths.append(os.path.join(root, filename))
        for path in yaml_paths:
            self._binding2path[os.path.basename(path)] = path


class DtshAutocomp(object):
    """Devicetree shell command line completer.

    Usually associated to the shell session's input buffer
    shared with GNU readline.

    The auto-completion state machine is made of:
    - the completion state, which is the sequence of possible input strings
      (hints) matching a given prefix
    - a model, which is the list of the actual possible objects matching the
      given prefix
    - a mode, that tags the model semantic (may help client code to avoid
      calling isinstance())
    """

    MODE_ANY: ClassVar[int] = 0
    MODE_DTSH_CMD: ClassVar[int] = 1
    MODE_DTSH_OPT: ClassVar[int] = 2
    MODE_DTSH_PAGE: ClassVar[int] = 3
    MODE_DT_NODE: ClassVar[int] = 4
    MODE_DT_PROP: ClassVar[int] = 5
    MODE_DT_BINDING: ClassVar[int] = 6

    @property
    @abstractmethod
    def count(self) -> int:
        """Current completions count.
        """

    @property
    @abstractmethod
    def hints(self) -> list[str]:
        """Current completion state.

        This is the list of completion strings that match the last prefix
        provided to autocomplete().
        """

    @property
    @abstractmethod
    def model(self) -> list:
        """Current completion model.

        This is the model objects correponding to the current completion hints.

        Permits rich implementation of the rl_completion_display_matches_hook()
        callback.
        """

    @property
    @abstractmethod
    def mode(self) -> int:
        """Current completion mode.

        Tag describing the current completion model.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset current completion state and model.
        """

    @abstractmethod
    def autocomplete(self,
                     cmdline: str,
                     prefix: str,
                     cursor: int = -1) -> list[str]:
        """Auto-complete command line.

        Arguments:
        cmdline -- the command line's current content
        prefix -- the prefix word to complete
        cursor -- required to get the full command line's state,
                  but unsupported

        Returns the completion state (hint strings) matching the prefix.
        """

    @staticmethod
    def autocomplete_with_nodes(prefix: str, shell: Dtsh) -> list[Node]:
        """Helper function to auto-complete with a list of nodes.

        Arguments:
        prefix -- the node path prefix
        shell -- the shell instance the nodes belong to

        Returns a list of matching nodes.
        """
        completions = list[Node]()

        if prefix:
            path_prefix = shell.realpath(prefix)
            if prefix.endswith('/'):
                path = path_prefix
            else:
                path = Dtsh.dirname(path_prefix)
        else:
            path_prefix = shell.pwd
            path = shell.pwd

        try:
            roots = [n for n in shell.ls(path) if n.path.startswith(path_prefix)]
            for child in roots:
                if len(child.path) > len(path_prefix):
                    completions.append(child)
        except DtshError:
            # No completions for invalid path.
            pass

        return completions

    @staticmethod
    def autocomplete_with_properties(node_prefix: str,
                                     prop_prefix: str,
                                     shell: Dtsh) -> list[Property]:

        completions = list[Property]()
        path_prefix = shell.realpath(node_prefix)
        if shell.isnode(path_prefix):
            node = shell.path2node(path_prefix)
            for _, p in node.props.items():
                if p.name.startswith(prop_prefix) and len(p.name) > len(prop_prefix):
                    completions.append(p)
        return completions


class DtshError(Exception):
    """Base exception for devicetree shell errors.
    """

    _msg: str
    _cause: Exception | None

    def __init__(self, msg: str, cause: Exception | None = None) -> None:
        """Create an error.

        Arguments:
        msg -- the error message
        cause -- the exception that caused this error, if any
        """
        super().__init__(msg)
        self._msg = msg
        self._cause = cause

    @property
    def msg(self) -> str:
        """The error message.
        """
        return self._msg

    @property
    def cause(self) -> Exception | None:
        """The error cause as an exception, or None.
        """
        return self._cause


class DtshCommandUsageError(DtshError):
    """A devicetree shell command execution has failed.
    """

    def __init__(self,
                 command: DtshCommand,
                 msg: str,
                 cause: Exception | None = None) -> None:
        """Create a new error.

        Arguments:
        command -- the failed command
        msg -- a message describing the usage error
        cause -- the cause exception, if any
        """
        super().__init__(msg, cause)
        self._command = command

    @property
    def command(self):
        """The failed command.
        """
        return self._command


class DtshCommandFailedError(DtshError):
    """A devicetree shell command execution has failed.
    """

    def __init__(self,
                 command: DtshCommand,
                 msg: str,
                 cause: Exception | None = None) -> None:
        """Create a new error.

        Arguments:
        command -- the failed command
        msg -- the failure message
        cause -- the failure cause, if any
        """
        super().__init__(msg, cause)
        self._command = command

    @property
    def command(self):
        """The failed command.
        """
        return self._command


class DtshCommandNotFoundError(DtshError):
    """The requested command is not supported by this devicetree shell.
    """

    def __init__(self, name: str) -> None:
        """Create a new error.

        Arguments:
        name -- the command name
        """
        super().__init__(f'command not found: {name}')
        self._name = name

    @property
    def name(self):
        """The not supported built-in name.
        """
        return self._name


class DtshSession(object):
    """Interactive devicetree shell session.
    """

    @property
    @abstractmethod
    def shell(self) -> Dtsh:
        """The session's shell.
        """

    @property
    @abstractmethod
    def vt(self) -> DtshVt:
        """The session's VT.
        """

    @property
    @abstractmethod
    def autocomp(self) -> DtshAutocomp:
        """The session's command line completer.
        """

    @property
    @abstractmethod
    def last_err(self) -> DtshError | None:
        """Last error triggered by a command execution.
        """

    @abstractmethod
    def run(self):
        """Enter interactive mode main loop.
        """

    @abstractmethod
    def close(self) -> None:
        """Close session, leaving interactive mode.
        """
