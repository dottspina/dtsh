# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Built-in 'uname' command."""


import os

from rich.table import Table
from rich.text import Text

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshUname, DtshVt
from dtsh.dtsh import DtshCommandUsageError
from dtsh.systools import GitHub, YamlFile
from dtsh.tui import DtshTui, DtshTuiBulletList, DtshTuiForm, DtshTuiMemo, DtshTuiYaml


class DtshBuiltinUname(DtshCommand):
    """Print current working node's path.

DESCRIPTION
The `uname` command will print *system* information, including:

- `kernel-version` (option **-v**): the Zephyr kernel version,
  e.g. `zephyr-3.1.0`; clicking the version string should open
  the corresponding release notes in the system default browser
- `machine` (option **-m**): based on the content of the board binding file,
  e.g. `nrf52840dk_nrf52840.yaml`; links to the board's DTS file and
  its Zephyr documentation
  (if [supported](https://docs.zephyrproject.org/latest/boards/index.html))
  should also show up
- `toolchain` (non *standard* option **-t**): build toolchain variant and
  version, based on the currently configured Zephyr command line developement
  environment (e.g. after sourcing `$ZEPHYR_BASE/zephyr-env.sh`);
  clicking the toolchain name or version should open related information
  in the system default browser

Retrieving this information may involve environment variables (e.g. `ZEPHYR_BASE`
or `ZEPHYR_TOOLCHAIN_VARIANT`), CMake cached variables, invoking `git` or GCC.

	|               | Environment variables    | CMake cache  | git | GCC |
	|---------------+--------------------------+--------------+-----+-----|
	| Zephyr kernel | ZEPHYR_BASE              |              | x   |     |
	| Toolchain     | ZEPHYR_TOOLCHAIN_VARIANT |              |     |     |
	|               | ZEPHYR_SDK_INSTALL_DIR   |              | x   |     |
	|               | GNUARMEMB_TOOLCHAIN_PATH |              |     | x   |
	| Board         | BOARD                    | BOARD_DIR    |     |     |
	|               |                          | CACHED_BOARD |     |     |

By default, `uname` will print brief system information: `kernel-version - machine`.

The **-l** option will enable a more detailed (aka *rich*) output.

To filter the printed information, explicitly set the **-v**, **-m** and
**-t** options.

Use the **-a** option to request all information.

Set the **--pager** option to page the command's output using the system pager
(only with **-l**).

EXAMPLES
Default brief system information:

```
/
❯ uname
Zephyr v3.1.0 - nrf52840dk_nrf52840
```

Filter detailed board (`machine`) information:

    /
	❯ uname -tl
	BOARD
		Board directory: $ZEPHYR_BASE/boards/arm/nrf52840dk_nrf52840
		Name:            nRF52840-DK-NRF52840 (Supported Boards)
		Board:           nrf52840dk_nrf52840 (DTS)

		nrf52840dk_nrf52840.yaml

		identifier: nrf52840dk_nrf52840
		name: nRF52840-DK-NRF52840
		type: mcu
		arch: arm
		ram: 256
		flash: 1024
		toolchain:
		  - zephyr
		  - gnuarmemb
		  - xtools
		supported:
		  - adc
		  - arduino_gpio
		  - arduino_i2c
		  - arduino_spi
		  - ble
		  - counter
		  - gpio
		  - i2c
		  - i2s
		  - ieee802154
		  - pwm
		  - spi
		  - usb_cdc
		  - usb_device
		  - watchdog
		  - netif:openthread

Filter detailed toolchain information:

    /
	❯ uname -tl
	TOOLCHAIN
		Path:    /mnt/platform/zephyr-rtos/SDKs/zephyr-sdk-0.15.1
		Variant: Zephyr SDK
		Version: v0.15.1
"""
    def __init__(self, shell: Dtsh):
        super().__init__(
            'uname',
            "print system information",
            True,
            [
                DtshCommandOption('use rich format', 'l', None, None),
                DtshCommandOption('print Zephyr kernel version',
                                  'v',
                                  'kernel-version',
                                  None),
                DtshCommandOption('print board',
                                  'm',
                                  'machine',
                                  None),
                DtshCommandOption('print toolchain',
                                  't',
                                  'toolchain',
                                  None),
                DtshCommandOption("print all information",
                                  'a',
                                  'all',
                                  None),
            ]
        )
        self._dtsh = shell

    @property
    def with_long_fmt(self) -> bool:
        return self.with_flag('-l')

    @property
    def with_kernel_version(self) -> bool:
        return self.with_flag('-v')

    @property
    def with_machine(self) -> bool:
        return self.with_flag('-m')

    @property
    def with_toolchain(self) -> bool:
        return self.with_flag('-t')

    @property
    def with_all(self) -> bool:
        return self.with_flag('-a')

    def parse_argv(self, argv: list[str]) -> None:
        """Overrides DtshCommand.parse_argv().
        """
        super().parse_argv(argv)

    def execute(self, vt: DtshVt) -> None:
        """Implements DtshCommand.execute().
        """
        if self.with_usage_summary:
            vt.write(self.usage)
            return
        if len(self._params) > 0:
            raise DtshCommandUsageError(self, 'too many parameters')

        if self.with_long_fmt:
            self._uname_long(vt)
        else:
            self._uname_brief(vt)

    def _uname_brief(self, vt: DtshVt) -> None:
        msg = ""
        no_with = not (
            self.with_flag('-v')
            or self.with_flag('-m')
            or self.with_flag('-t')
        )
        if self.with_all or no_with or self.with_kernel_version:
            if self._dtsh.uname.zephyr_kernel_tags:
                msg += f"Zephyr {self._dtsh.uname.zephyr_kernel_tags[0]}"
            elif self._dtsh.uname.zephyr_kernel_rev:
                msg += f"Zephyr {self._dtsh.uname.zephyr_kernel_rev}"
            else:
                msg += "Unknown"
        if self.with_all or no_with or self.with_machine:
            if msg:
                msg += " - "
            if self._dtsh.uname.board:
                msg += f"{self._dtsh.uname.board}"
            else:
                msg += "Unknown"
        if self.with_all or self.with_toolchain:
            if msg:
                if self._dtsh.uname.zephyr_toolchain:
                    msg += f" ({self._dtsh.uname.zephyr_toolchain})"
                else:
                    msg += " (Unknown)"
            else:
                if self._dtsh.uname.zephyr_toolchain:
                    msg += f"{self._dtsh.uname.zephyr_toolchain}"
                else:
                    msg += "Unknown"
        vt.write(msg)

    def _uname_long(self, vt: DtshVt) -> None:
        view = DtshTuiMemo()
        # When no explicit choice, and long format,
        # we'll show all available info.
        def_all = not (self.with_flag('-v')
                       or self.with_flag('-m')
                       or self.with_flag('-t'))

        if self.with_all or def_all or self.with_kernel_version:
            view.add_entry("zephyr kernel", self._mk_layout_zephyr_kernel())

        if self.with_all or def_all or self.with_toolchain:
            if self._dtsh.uname.zephyr_toolchain:
                content = ZephyrToolchainForm(self._dtsh.uname).as_renderable()
            else:
                content = None
            view.add_entry("toolchain", content)

        if self.with_all or def_all or self.with_machine:
            view.add_entry("board", self._mk_layout_board())

        view.show(vt, self.with_pager)

    def _mk_layout_zephyr_kernel(self) -> Table | None:
        if self._dtsh.uname.zephyr_base:
            layout = DtshTui.mk_grid(1)
            layout.add_row(ZephyrKernelForm(self._dtsh.uname).as_renderable())
            layout.add_row()
            if self._dtsh.uname.dt_binding_dirs:
                r_list = DtshTuiBulletList("Bindings search path:")
                for path in self._dtsh.uname.dt_binding_dirs:
                    if path.startswith(self._dtsh.uname.zephyr_base):
                        path = path.replace(self._dtsh.uname.zephyr_base, "$ZEPHYR_BASE")
                    r_list.add_item(path)
                layout.add_row(r_list.as_renderable())
            else:
                r_warn = DtshTui.mk_txt_warn("Empty bindings search path !")
                layout.add_row(r_warn)
            return layout
        return None

    def _mk_layout_board(self) -> Table | None:
        if self._dtsh.uname.board:
            layout = DtshTui.mk_grid(1)
            layout.add_row(ZephyrBoardForm(self._dtsh.uname).as_renderable())
            if self._dtsh.uname.board_binding_file:
                if os.path.isfile(self._dtsh.uname.board_binding_file):
                    w_yaml = DtshTuiYaml(self._dtsh.uname.board_binding_file,
                                         with_title=True)
                    layout.add_row()
                    layout.add_row(w_yaml.as_renderable())
            return layout
        return None


class ZephyrKernelForm(DtshTuiForm):
    """Simple form for Zephyr's path, revision and tags.
    """

    def __init__(self, uname: DtshUname) -> None:
        """Initialize the form.

        Arguments:
        uname -- dtsh system-like information
        """
        super().__init__()
        if not uname.zephyr_base:
            # We won't get far without ZEPHYR_BASE.
            return
        gh = GitHub()
        self.add_field('Path', uname.zephyr_base)
        if uname.zephyr_kernel_tags:
            # Tags or version.
            version = uname.zephyr_kernel_version
            if version:
                r_version = DtshTui.mk_txt_link(
                    version,
                    gh.get_tag(version),
                    style='dtsh.zephyr'
                )
                tags = uname.zephyr_kernel_tags.copy()
                tags.remove(version)
                if tags:
                    r_tags = DtshTui.mk_txt(f" ({', '.join(tags)})")
                    r_version.append_text(r_tags)
                self.add_field_rich("Version", r_version)
            else:
                self.add_field("Tags", ', '.join(uname.zephyr_kernel_tags))
        if uname.zephyr_kernel_rev:
            r_revision = DtshTui.mk_txt_link(
                uname.zephyr_kernel_rev,
                gh.get_commit(uname.zephyr_kernel_rev),
                style='default' if uname.zephyr_kernel_version else 'dtsh.commit'
            )
        else:
            # Show revision field even when information is unavailable.
            r_revision = DtshTui.mk_txt_dim("Unknown")
        self.add_field_rich("Revision", r_revision)


class ZephyrToolchainForm(DtshTuiForm):
    """Simple form for Zephyr's path, revision and tags.
    """

    def __init__(self, uname: DtshUname) -> None:
        """Initialize the form.

        Requires: zephyr_toolchain
        Optional:
        - zephyr_sdk_version, zephyr_sdk_dir
        or
        - gnuarm_version, gnuarm_dir

        Arguments:
        uname -- dtsh system-like information
        """
        super().__init__()
        if not uname.zephyr_toolchain:
            # We won't get far if we don't know the toolchain variant.
            return

        r_version = None
        if uname.zephyr_toolchain == 'zephyr':
            # Zephyr SDK toolchain.
            self.add_field('Path', uname.zephyr_sdk_dir)
            r_variant = DtshTui.mk_txt_link(
                "Zephyr SDK",
                "https://docs.zephyrproject.org/latest/develop/toolchains/zephyr_sdk.html",
                style='dtsh.zephyr'
            )
            if uname.zephyr_sdk_version:
                sdk_version = f"v{uname.zephyr_sdk_version}"
                r_version = DtshTui.mk_txt_link(
                    sdk_version,
                    f"https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/{sdk_version}",
                    style='dtsh.zephyr'
                )
            else:
                r_version = DtshTui.mk_txt_dim("Unknown")

        elif uname.zephyr_toolchain == 'gnuarmemb':
            # GNU Arm Embedded toolchain.
            self.add_field('Path', uname.gnuarm_dir)
            r_variant = DtshTui.mk_txt_link(
                "GNU Arm Embedded",
                "https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain",
                style='dtsh.gnuarmemb'
            )
            if uname.gnuarm_version:
                r_version = DtshTui.mk_txt(uname.gnuarm_version)
            else:
                r_version = DtshTui.mk_txt_dim("Unknown")
        else:
            r_variant = DtshTui.mk_txt_dim("Unknown")

        self.add_field_rich("Variant", r_variant)
        if r_version:
            self.add_field_rich("Version", r_version)


class ZephyrBoardForm(DtshTuiForm):
    """Simple form for Zephyr's path, revision and tags.
    """

    def __init__(self, uname: DtshUname) -> None:
        """Initialize the form.

        Requires: uname.board
        Optional: uname.bord_dir

        Arguments:
        uname -- dtsh system-like information
        """
        super().__init__()
        if not uname.board_dir:
            # We won't get far if without at least the directory.
            return

        board_dir = uname.board_dir
        if uname.zephyr_base and board_dir.startswith(uname.zephyr_base):
            board_dir = board_dir.replace(uname.zephyr_base, "$ZEPHYR_BASE")
        self.add_field("Board directory", board_dir)

        # Remaining fields depend on the YAML file content.
        if not uname.board_binding_file:
            return
        # Remaining fields depend on BOARD (e.g. nrf52840dk_nrf52840).
        if not uname.board:
            return

        yaml_file = YamlFile(uname.board_binding_file)

        r_name = None
        board_name = yaml_file.get('name')
        if board_name:
            r_name = DtshTui.mk_txt_bold(board_name)
            if uname.zephyr_base and uname.board_dir.startswith(uname.zephyr_base):
                # We then assume it's a Zephyr board with online doc.
                arch = yaml_file.get('arch')
                if arch:
                    url = f'https://docs.zephyrproject.org/latest/boards/{arch}/{uname.board}/doc/index.html'
                    r_www = DtshTui.mk_txt_link(
                        "Supported Boards",
                        url,
                        style='dtsh.zephyr'
                    )
                    r_name = Text().append_text(r_name)
                    r_name.append_text(DtshTui.mk_txt(' ('))
                    r_name.append_text(r_www)
                    r_name.append_text(DtshTui.mk_txt(')'))
        else:
            r_name = DtshTui.mk_txt_dim("Unknown")
        self.add_field_rich("Name", r_name)

        r_board = DtshTui.mk_txt(uname.board, style='dtsh.board')
        if uname.board_dts_file:
            r_dts = DtshTui.mk_txt_link(
                "DTS",
                f'file:{uname.board_dts_file}',
                style='dtsh.default'
            )
            r_board.append_text(DtshTui.mk_txt(' ('))
            r_board.append_text(r_dts)
            r_board.append_text(DtshTui.mk_txt(')'))
        self.add_field_rich("Board", r_board)
