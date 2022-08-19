# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell rich output."""


from abc import abstractmethod

from devicetree.edtlib import Node, Binding

from rich.color import Color
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshVt


# Common colors.
#
# See:
# - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code#Colors

COLOR_DEFAULT = Color.default()
COLOR_GREY = Color.from_ansi(254)
COLOR_DISABLED = Color.default()

COLOR_NODE_PATH = Color.default()
COLOR_NODE_NICKNAME = Color.default()
COLOR_NODE_ADDR = Color.default()

COLOR_NODE_ALIAS = Color.from_ansi(45)
COLOR_NODE_LABELS = Color.from_ansi(39)
COLOR_NODE_LABEL = Color.from_ansi(39)

COLOR_NODE_DESC = Color.from_ansi(97)
COLOR_NODE_COMPAT = Color.from_ansi(37)

COLOR_NODE_STATUS_OKAY = Color.from_ansi(43)
COLOR_NODE_STATUS_DIS = Color.default()

COLOR_PATH_SEGMENT = Color.from_ansi(31)
COLOR_PATH_ANCHOR = Color.from_ansi(39)

PYGMENTS_THEME = 'monokai'


class DtshTheme(object):
    """
    """

    STYLE_DEFAULT = Style(color=Color.default())
    STYLE_BOLD = Style(bold=True)
    STYLE_DIM = Style(dim=True)
    STYLE_ITALIC = Style(italic=True)
    STYLE_STRIKE = Style(strike=True)

    # Apply to a render-able to style it as disabled node/path.
    STYLE_DISABLED = Style(color=COLOR_DISABLED, dim=True)

    STYLE_PATH_SEGMENT = Style(color=COLOR_PATH_SEGMENT)
    STYLE_PATH_ANCHOR = Style(color=COLOR_PATH_ANCHOR, bold=True)

    STYLE_NODE_NICK = Style(color=COLOR_NODE_NICKNAME)
    STYLE_NODE_ADDR = Style(color=COLOR_NODE_ADDR)
    STYLE_NODE_LABEL = Style(color=COLOR_NODE_LABEL)
    STYLE_NODE_LABELS = Style(color=COLOR_NODE_LABELS, italic=True)
    STYLE_NODE_ALIAS = Style(color=COLOR_NODE_ALIAS)
    STYLE_NODE_COMPAT = Style(color=COLOR_NODE_COMPAT)
    STYLE_NODE_DESC = Style(color=COLOR_NODE_DESC)

    WCHAR_PROMPT = '\u276f'
    WCHAR_ELLIPSIS = '\u2026'
    WCHAR_COPYRIGHT = '\u00a9'
    WCHAR_HYPHEN = '\u2014'
    WCHAR_DASH = '\ufe4d'

    # Set to None to remove ...
    TXT_HOLDER = Text('\ufe4d', Style(color=Color.default(), dim=True))

    OPTION_SPARSE_PROMPT = True

    @staticmethod
    def get_node_nickname(node: Node) -> str:
        """Get a node's nickname.

        Returns the node's name with the unit address part striped.
        """
        if node.unit_addr is not None:
            return node.name[0:node.name.rfind('@')]
        return node.name

    @staticmethod
    def get_str_summary(txt: str) -> str:
        """Get 1st line of text as summary.

        Arguments:
        txt -- a long multi-line text

        Returns a single line summary.
        """
        desc_lines = txt.split('\n')
        desc = desc_lines[0]
        if len(desc_lines) > 1:
            if desc.endswith('.'):
                desc = desc[:-1]
            desc += DtshTheme.WCHAR_ELLIPSIS
        return desc

    @staticmethod
    def mk_txt(txt: str = '') -> Text:
        """Create a rich text with default style.
        """
        return Text(txt, DtshTheme.STYLE_DEFAULT)

    @staticmethod
    def mk_dim(txt: str) -> Text:
        """Create a rich text with dim style.
        """
        return Text(txt, DtshTheme.STYLE_DIM)

    @staticmethod
    def mk_bold(txt: str) -> Text:
        """Create a rich text with bold style.
        """
        return Text(txt, DtshTheme.STYLE_BOLD)

    @staticmethod
    def mk_italic(txt: str) -> Text:
        """Create a rich text with italic style.
        """
        return Text(txt, DtshTheme.STYLE_ITALIC)

    @staticmethod
    def conceal_txt(txt: Text) -> None:
        """
        """
        txt.stylize(DtshTheme.STYLE_DISABLED)

    @staticmethod
    def emphasize_txt(txt: Text) -> None:
        """Apply italic style to rich text.
        """
        txt.stylize(DtshTheme.STYLE_ITALIC)

    @staticmethod
    def strike_txt(txt: Text) -> None:
        """Apply italic style to rich text.
        """
        txt.stylize(DtshTheme.STYLE_STRIKE)

    @staticmethod
    def mk_ansi_prompt(has_error: bool = False) -> str:
        """Create an ANSI 255 colors compatible prompt.

        Arguments:
        has_error -- True if last command execution has failed.

        Returns a prompt compatible with ANSI 255 colors terminals.
        """
        # Using ANSI escape codes in input() breaks the GNU readline cursor.
        #
        # The hand-made prompt bellow uses the RL_PROMPT_{START,STOP}_IGNORE markers
        # to keep the readline state consistent.
        #
        # <SGR_SEC> := <CSI><n1, n2, ...>m
        # <CSI> := ESC[
        #       := \x1b[
        #
        # <START_IGNORE> := '\001'
        # <END_IGNORE> := '\002'
        #
        # See:
        # - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code
        # - https://wiki.hackzine.org/development/misc/readline-color-prompt.html
        # - https://en.wikipedia.org/w/index.php?title=ANSI_escape_code#Colors
        #
        # We assume terminal has at least 255 colors.
        if has_error:
            sgr_color = '38;5;88'
        else:
            sgr_color = '38;5;99'
        return f'\001\x1b[{sgr_color};1m\002{DtshTheme.WCHAR_PROMPT}\001\x1b[0m\002 '

    @staticmethod
    def mk_command_hints_display(hints: list[DtshCommand]) -> Table:
        """Layout command completion hints.

        Arguments:
        hints -- a command list to display as hints

        Returns a rich table.
        """
        tab = DtshTheme.mk_grid(2)
        for cmd in hints:
            tab.add_row(DtshTheme.mk_txt(cmd.name), DtshTheme.mk_dim(cmd.desc))
        return tab

    @staticmethod
    def mk_option_hints_display(hints: list[DtshCommandOption]) -> Table:
        """Layout option completion hints.

        Arguments:
        hints -- an option list to display as hints

        Returns a rich table.
        """
        tab = DtshTheme.mk_grid(2)
        for opt in hints:
            tab.add_row(DtshTheme.mk_txt(opt.usage), DtshTheme.mk_dim(opt.desc))
        return tab

    @staticmethod
    def mk_node_hints_display(hints: list[Node]) -> Table:
        """Layout node completion hints.

        Arguments:
        hints -- a node list to display as hints

        Returns a rich table.
        """
        tab = DtshTheme.mk_grid(3)
        for node in hints:
            nick = DtshTheme.mk_txt(DtshTheme.get_node_nickname(node))
            if node.unit_addr is not None:
                addr = DtshTheme.mk_txt(hex(node.unit_addr))
            else:
                addr = None
            if node.description:
                desc_str = DtshTheme.get_str_summary(str(node.description))
                desc = DtshTheme.mk_txt(f'{desc_str}')
            else:
                desc = None
            if node.status == 'disabled':
                DtshTheme.conceal_txt(nick)
                if addr:
                    DtshTheme.conceal_txt(addr)
                if desc:
                    DtshTheme.conceal_txt(desc)
            tab.add_row(nick, addr, desc)
        return tab

    @staticmethod
    def mk_property_hints_display(hints: list[Node]) -> Table:
        """Layout property completion hints.

        Arguments:
        hints -- a property list to display as hints

        Returns a rich table.
        """
        # ISSUE: edtlib would raise p.description.strip() not defined on NoneType,
        # let's rely on p.spec.
        tab = DtshTheme.mk_grid(2)
        return tab

    @staticmethod
    def mk_binding_hints_display(hints: list[Binding]) -> Table:
        """Layout bindings completion hints.

        Arguments:
        hints -- a binding list to display as hints

        Returns a rich table.
        """
        tab = DtshTheme.mk_grid(2)
        for binding in hints:
            txt_compat = DtshTheme.mk_txt(binding.compatible)
            if binding.description:
                desc_str = DtshTheme.get_str_summary(binding.description)
                txt_desc = DtshTheme.mk_dim(desc_str)
            else:
                txt_desc = None
            tab.add_row(txt_compat, txt_desc)
        return tab

    @staticmethod
    def mk_grid(cols: int, expand: bool = False) -> Table:
        """Create a grid layout.

        Arguments:
        cols -- number of columns
        expand -- if True, the layout will expand to the available space
        """
        grid = Table.grid(padding=(0, 1))
        for _ in range(0, cols):
            grid.add_column()
        return grid

    @staticmethod
    def mk_table(cols: int, expand: bool = False) -> Table:
        """Create a table layout.

        Arguments:
        cols -- number of columns
        expand -- if True, the layout will expand to the available space
        """
        tab = Table(
            box=None, # Default: Box.HEAVY_HEAD
            padding=(0, 1),
            pad_edge=False, # Default: True
            expand=expand,
            show_header=False, # Default: True
            show_footer=False,
            show_edge=False, # Default: True
            show_lines=False,
            leading=0,
            highlight=False
        )
        for _ in range(0, cols):
            tab.add_column()
        return tab

    @staticmethod
    def mk_wide_table() -> Table:
        """Create a wide table layout (for e.g. man pages).

        Should:
        - expand to all horizontal space
        - define 3 columns justified as left, center, right.
        """
        tab = Table(
            box=None, # Default: Box.HEAVY_HEAD
            padding=0,
            pad_edge=False, # Default: True
            expand=True,
            show_header=False, # Default: True
            show_footer=False,
            show_edge=False, # Default: True
            show_lines=False,
            leading=0,
            highlight=False
        )
        tab.add_column(justify='left', style=DtshTheme.STYLE_DEFAULT, ratio=1)
        tab.add_column(justify='center', style=DtshTheme.STYLE_DEFAULT, ratio=1)
        tab.add_column(justify='right', style=DtshTheme.STYLE_DEFAULT, ratio=1)
        return tab

    @staticmethod
    def mk_node_table(expand: bool = False) -> Table:
        """Create a table layout for node list views.

        Arguments:
        expand -- if True, the layout will expand to the available space
        """
        return DtshTheme.mk_table(7, expand=expand)

    @staticmethod
    def mk_node_tree(anchor: Table | Text | str) -> Tree:
        """Create a table layout for node list views.

        Arguments:
        anchor -- the view for the tree's root.
        """
        return Tree(anchor)

    @staticmethod
    def mk_node_path(path:str) -> Text:
        """Create a rich node path.

        Arguments:
        path -- the node path

        Returns a rich text.
        """
        if path == '/':
            return Text('/', DtshTheme.STYLE_PATH_ANCHOR)

        nodename = Dtsh.nodename(path)
        dirpath = Dtsh.dirname(path)
        if not dirpath.endswith('/'):
            dirpath += '/'

        return Text().append_tokens(
            [
                (f'{dirpath}', DtshTheme.STYLE_PATH_SEGMENT),
                (nodename, DtshTheme.STYLE_PATH_ANCHOR),
            ]
        )

    @staticmethod
    def mk_node_nickname(node: Node, with_status: bool = True) -> Text:
        nick = DtshTheme.get_node_nickname(node)
        txt = Text(nick, DtshTheme.STYLE_NODE_NICK)
        if with_status and (node.status == 'disabled'):
            DtshTheme.conceal_txt(txt)
        return txt

    @staticmethod
    def mk_node_address(node: Node,
                        with_status: bool = True,
                        with_holder: bool = True) -> Text | None:
        if node.unit_addr is not None:
            txt = Text(hex(node.unit_addr), DtshTheme.STYLE_NODE_ADDR)
            if with_status and (node.status == 'disabled'):
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_label(node: Node,
                      with_status: bool = True,
                      with_holder: bool = True) -> Text | None:
        if node.label is not None:
            txt = Text(node.label, DtshTheme.STYLE_NODE_LABEL)
            if with_status and (node.status == 'disabled'):
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_labels(node: Node,
                       with_status: bool = True,
                       with_holder: bool = True) -> Text | None:
        if node.labels:
            txt = DtshTheme.mk_txt()
            N = len(node.labels)
            i = 0
            for label in node.labels:
                txt.append(label, DtshTheme.STYLE_NODE_LABELS)
                if i < (N - 1):
                    txt.append(', ', DtshTheme.STYLE_DEFAULT)
                i += 1
            if with_status and (node.status == 'disabled'):
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_aliases(node: Node,
                        with_status: bool = True,
                        with_holder: bool = True) -> Text | None:
        if node.aliases:
            txt = DtshTheme.mk_txt()
            N = len(node.aliases)
            i = 0
            for alias in node.aliases:
                txt.append(alias, DtshTheme.STYLE_NODE_ALIAS)
                if i < (N - 1):
                    txt.append(', ', DtshTheme.STYLE_DEFAULT)
                i += 1
            if with_status and (node.status == 'disabled'):
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_compat(node: Node,
                       with_status: bool = True,
                       with_holder: bool = True) -> Text | None:
        if node.matching_compat:
            txt = Text(node.matching_compat, DtshTheme.STYLE_NODE_COMPAT)
            if with_status and node.status == 'disabled':
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_desc(node: Node,
                     with_status: bool = True,
                     with_holder: bool = True) -> Text | None:
        if node.description:
            desc_str = DtshTheme.get_str_summary(str(node.description))
            txt = Text(desc_str, DtshTheme.STYLE_NODE_DESC)
            if with_status and node.status == 'disabled':
                DtshTheme.conceal_txt(txt)
            return txt
        if with_holder:
            return DtshTheme.TXT_HOLDER
        return None

    @staticmethod
    def mk_node_row(tab: Table,
                    node: Node,
                    with_status: bool = True,
                    with_holder: bool = True) -> None:
        """
        """
        tab.add_row(
            DtshTheme.mk_node_nickname(node, with_status),
            DtshTheme.mk_node_address(node, with_status, with_holder),
            DtshTheme.mk_node_label(node, with_status, with_holder),
            DtshTheme.mk_node_labels(node, with_status, with_holder),
            DtshTheme.mk_node_aliases(node, with_status, with_holder),
            DtshTheme.mk_node_compat(node, with_status, with_holder),
            DtshTheme.mk_node_desc(node, with_status, with_holder)
        )

    @staticmethod
    def mk_node_infotip(node: Node,
                        width: int,
                        with_status: bool = True) -> Table:
        """Appropriate for tree views.
        """
        tab = DtshTheme.mk_grid(3)
        if width > 0:
            tab.columns[1].width = width
        nick = DtshTheme.mk_node_nickname(node, with_status)
        addr = DtshTheme.mk_node_address(node, with_status, with_holder=False)
        compat = DtshTheme.mk_node_compat(node, with_status,  with_holder=False)
        tab.add_row(addr, nick, compat)
        return tab

    @staticmethod
    def mk_yaml_view(path: str, theme: str = PYGMENTS_THEME) -> Syntax:
        return Syntax.from_path(path, lexer='yaml', theme=theme,)


class DtshRichView(object):
    """Abstract rich view.
    """

    @abstractmethod
    def show(self, vt: DtshVt, shell: Dtsh, with_pager: bool = False) -> None:
        """Print view to session with rich output support.
        """


class DtshNodeListView(DtshRichView):
    """View of a devicetree node list.
    """

    def __init__(self,
                 node_map: dict[str, list[Node]],
                 with_no_content: bool,
                 with_rich_fmt: bool,
                 ) -> None:
        """Create a new list view.

        Arguments:
        node_map -- maps a list of path to their child nodes
        with_no_content -- do not view nodes content
        with_rich_fmt -- use rich format
        """
        super().__init__()
        self._node_map = node_map
        self._no_content = with_no_content
        self._rich_fmt = with_rich_fmt

    def show(self, vt: DtshVt, shell: Dtsh, with_pager: bool = False) -> None:
        """Overrides DtshRichView.show().
        """
        if len(self._node_map) > 0:
            if with_pager:
                vt.pager_enter()
            if self._rich_fmt:
                self._print_rich(vt, shell)
            else:
                self._print_raw(vt)
            if with_pager:
                vt.pager_exit()

    def _print_raw(self, vt: DtshVt):
        """
        """
        N = len(self._node_map)
        i = 0
        for path, nodes in self._node_map.items():
            if self._no_content:
                vt.write(f"{path}")
            else:
                if N > 1:
                    vt.write(f"{path}:")
                for node in nodes:
                    vt.write(f'{node.path}')
                if i < (N - 1):
                    vt.write()
                i += 1

    def _print_rich(self, vt: DtshVt, shell: Dtsh):
        """
        """
        if self._no_content:
            tab = DtshTheme.mk_node_table()
            for path, _ in self._node_map.items():
                node = shell.path2node(path)
                DtshTheme.mk_node_row(tab, node)
            vt.write(tab)
        else:
            N = len(self._node_map)
            i = 0
            for path, content in self._node_map.items():
                vt.write(f"{path}:", style=DtshTheme.STYLE_BOLD)
                if content:
                    tab = DtshTheme.mk_node_table()
                    for node in content:
                        DtshTheme.mk_node_row(tab, node)
                    vt.write(tab)
                if i < (N - 1):
                    vt.write()
                i += 1


class DtshNodeTreeView(DtshRichView):
    """View of a devicetree node content as a tree.
    """

    def __init__(self,
                 root: Node,
                 level: int,
                 with_rich_fmt: bool) -> None:
        """Create a new tree view.

        Arguments:
        root -- maps a list of path to their child nodes
        level -- maximum display depth, 0 to follow all non disabled nodes
        with_rich_fmt -- use rich format
        """
        super().__init__()
        self._root = root
        self._level = level
        self._rich_fmt = with_rich_fmt
        self._depth = 0

    def show(self, vt: DtshVt, shell: Dtsh, with_pager: bool = False) -> None:
        """Overrides DtshRichView.show().
        """
        if with_pager:
            vt.pager_enter()

        if self._rich_fmt:
            anchor = DtshTheme.mk_node_infotip(self._root, 0)
        else:
            anchor = Text(self._root.name, DtshTheme.STYLE_BOLD)
        tree = DtshTheme.mk_node_tree(anchor)

        self._follow_node_branch(self._root, tree)
        vt.write(tree)

        if with_pager:
            vt.pager_exit()

    def _follow_node_branch(self,
                            root: Node,
                            tree: Tree) -> None:
        """
        """
        # Increase depth when following a branch.
        self._depth += 1

        # Maximum length of child nodes nickname.
        width = self._get_branch_width(root)

        for _, node in root.children.items():
            if self._rich_fmt:
                anchor = DtshTheme.mk_node_infotip(node, width)
            else:
                anchor = node.name
            branch = tree.add(anchor)

            if (self._level == 0) or (self._depth < self._level):
                if node.status != 'disabled':
                    self._follow_node_branch(node, branch)

        # Decrease depth on return.
        self._depth -= 1

    def _get_branch_width(self, root: Node) -> int:
        width = 0
        for _, node in root.children.items():
            nick = DtshTheme.get_node_nickname(node)
            w = len(nick)
            if w > width:
                width = w
        return width
