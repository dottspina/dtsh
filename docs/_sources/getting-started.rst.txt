.. _dtsh-getting-started:

Getting Started Guide
#####################

This simple guide covers DTSh's installation, configuration and basic usage.


.. _dtsh-install:

Install DTSh
************

DTSh runs on Linux, macOS and Windows with Python 3.8 to 3.11.

It can be installed in *some* Zephyr development environment,
or standalone in any Python environment.

.. warning::

   On **Windows**, the `readline API <Python readline_>`_, on which DTSh relies for auto-completion
   and command history, is no longer distributed with the Python Standard Library: as a consequence,
   the user experience will be significantly degraded on this platform.
   This is `known issue <DTSh-Issue gnureadline_>`_ without workaround.

   Prefer `WSL <WSL_>`_ if possible.


.. _dtsh-requirements:

Requirements
============

Only prerequisite is the Python devicetree library, part of the Zephyr project.
Other run-time requirements are simple external dependencies available from PyPI.


.. _dtsh-python-devicetree:

python-devicetree
-----------------

To parse DTS and binding files into Devicetree models, DTSh relies on the
`python-devicetree <Zephyr-python-devicetree_>`_ library (``edtlib``),
part of `Zephyr's DTS tooling <Zephyr-Devicetree Tooling_>`_.

Although this API may eventually become a *standalone source code library*,
it is currently not a priority of the Zephyr project,
and the `PyPI package <PyPI-devicetree_>`_ is no longer updated (the latest version is April 2022).

DTSh therefore re-distributes `snapshots <https://github.com/dottspina/dtsh/tree/dtsh-next/src/devicetree>`_
of this library along with its own implementation.
This works but `is not an ideal situation <DTSh-Issue python-devicetree_>`_.


.. _dtsh-dependencies:

External Dependencies
---------------------

.. list-table:: External Dependencies
   :widths: auto
   :align: center

   * - Textualize's *rich* library for *beautiful formatting*
     - `rich <PyPI-rich_>`_
   * - PyYAML, YAML parser for Python
     - `PyYAML <PyPI-PyYAML_>`_
   * - Stand-alone GNU readline module (macOS only)
     - `gnureadline <PyPI-gnureadline_>`_


.. _dtsh-installation:

Installation
============

There are basically two types of installation:

- *alongside* West, in a Python virtual environment you use for Zephyr development
- *standalone* in any Python virtual environment


.. _dtsh-install-alongside:

Install Alongside West
----------------------

This method installs DTSh in a Python virtual environment that belongs to a West workspace,
(where the `west` command itself is installed, with other dependencies).

Assuming you've followed Zephyr's `Getting Started Guide <Zephyr-Getting Started_>`_,
the workspace should look like this::

   zephyrproject/
   ├── .venv
   ├── .west
   ├── bootloader
   ├── modules
   ├── tools
   └── zephyr

To install DTSh *alongside West*, activate this ``zephyrproject/.venv`` environment
before running ``pip``:

.. code-block:: sh

   # Active the Python virtual environment if not already done.
   . zephyrproject/.venv/bin/activate

   # Install latest version of DTSh from PyPI.
   pip install -U dtsh


.. tip::

   Or just run ``pip install -U dtsh`` from the same prompt where you usually enter ``west`` commands.


.. _dtsh-install-standalone:

Standalone Installation
-----------------------

This method installs DTSh in a dedicated Python virtual environment: it's a little less
convenient but avoids installing anything in a development environment you actually depend on.

.. code-block:: sh

   # Initialize Python virtual environment.
   mkdir dtsh
   cd dtsh
   python -m venv .venv

   # Activate and update system tools.
   . .venv/bin/activate
   pip install -U pip setuptools

   # Install DTSh from PyPI.
   pip install -U dtsh


.. _dtsh-usage:

Usage
*****

Once installed, the Devicetree Shell is available as the ``dtsh`` command:

.. code-block:: none

   $ dtsh -h
   usage: dtsh [-h] [-b DIR] [-u] [--preferences FILE] [--theme FILE] [-c CMD] [-f FILE] [-i] [DTS]

   shell-like interface with Devicetree

   options:
     -h, --help            show this help message and exit

   open a DTS file:
     -b DIR, --bindings DIR
                           directory to search for binding files
     DTS                   path to the DTS file

   user files:
     -u, --user-files      initialize per-user configuration files and exit
     --preferences FILE    load additional preferences file
     --theme FILE          load additional styles file

   session control:
     -c CMD                execute CMD at startup (may be repeated)
     -f FILE               execute batch commands from FILE at startup
     -i, --interactive     enter interactive loop after batch commands

We'll first confirm that the installation went well with a simple but typical usage,
before tackling a few other scenarios.


.. _dtsh-usage-default:

Typical Use
===========

Early at build-time, during the `configuration phase <Zephyr-Configuration Phase_>`_,
Zephyr *assembles* the final `devicetree <DTSpec-The Devicetree_>`_ that will represent
the system hardware during the actual build phase.

This devicetree is saved in `Devicetree Source Format <DTSpec-DTS_>`_ (DTS)
in ``build/zephyr/zephyr.dts`` for *debugging* purpose.

The typical DTSh's use case is to open this DTS file generated at build-time, e.g.:

.. code-block:: none

   $ cd zephyr/samples/sensor/bme680
   $ cmake -B build -DBOARD=nrf52840dk_nrf52840
   $ dtsh build/zephyr/zephyr.dts
   dtsh (0.2.1): A Devicetree Shell
   How to exit: q, or quit, or exit, or press Ctrl-D

   /
   > ls -l
    Name              Labels          Binding
    ───────────────────────────────────────────────────────
    chosen
    aliases
    soc
    pin-controller    pinctrl         nordic,nrf-pinctrl
    entropy_bt_hci    rng_hci         zephyr,bt-hci-entropy
    sw-pwm            sw_pwm          nordic,nrf-sw-pwm
    cpus
    leds                              gpio-leds
    pwmleds                           pwm-leds
    buttons                           gpio-keys
    connector         arduino_header  arduino-header-r3
    analog-connector  arduino_adc     arduino,uno-adc

The above example should *always* work:

- regardless of the installation method, ``cmake`` being sufficient for the configuration phase
- regardless of whether ``ZEPHYR_BASE`` is set
- regardless of whether you target a `supported board <Zephyr-Boards_>`_
  or a `custom board <Zephyr-Board Porting Guide_>`_

Here, DTSh retrieves *all it needs*, and especially where to search for the bindings files,
from the CMake cache content in ``CMakeCache.txt``::

   build
   ├── CMakeCache.txt
   └── zephyr
       └── zephyr.dts

.. tip::

   - In this context, no need to pass the DTS file path to DTSh: by default it will try
     to open the devicetree at ``build/zephyr/zephyr.dts``;
     ``dtsh /path/to/project/build/zephyr/zephyr.dts`` would also work,
     you don't need to call ``dtsh`` from the project's root
   - To open *your* devicetree: ``cd <project> && cmake -B build -DBOARD=<board> && dtsh``,
     or if using West ``cd <project> && west build && dtsh``


.. _dtsh-usage-others:

Other Uses
==========

As we've seen, DTSh first tries to retrieve the bindings Zephyr has used at build-time,
when the DTS file was generated, from the CMake cache.
This is the most straight forward way to get a complete and legit bindings search path.

When this fails, DTSh will then try to work out the search path
Zephyr would use if it were to generate the DTS *now*
(`Where Bindings Are Located <Zephyr-Where Bindings Are Located_>`_): bindings found in
``$ZEPHYR_BASE/dts/bindings`` and other *default* directories should still cover
the most simple use cases (e.g. Zephyr samples).

.. code-block:: none

   $ export ZEPHYR_BASE=/path/to/zephyrproject/zephyr
   $ dtsh /path/to/zephyr.dts

This default behavior does not address all situations, though:

- you may need additional bindings files from a custom location,
  or explicitly set the ``DTS_ROOT`` CMake variable
- you're not working with Zephyr

For these use cases, the ``-b --bindings`` option permits to explicitly enumerate all the directories
to search in:

   $ dtsh --bindings dir1 --bindings dir2 foobar.dts

Where:

- ``dir1`` and ``dir1``, and their sub-directories, shall contain all necessary YAML binding files
  in Zephyr's `Devicetree Binding Syntax <Zephyr-Binding Syntax_>`_,
  even if not working with Zephyr
- one of these directories shall contain a valid vendors file, e.g. ``dir1/vendor-prefixes.txt``


.. _dtsh-usage-batch:

Batch Mode
==========

For scripting and automation, DTSh can also be used non-interactively by passing:

 - a series of commands to execute at startup: ``-c CMD1 -c CMD2``
 - or a file containing such commands: ``-f FILE``

The ``-i --interactive`` option then permits to enter the interactive loop after the batch commands have been executed.

For example, to list the contents of the root of the devicetree and then change
to another directory, before entering the interactive loop, you can use the
following command:

.. code-block:: none

   $ dtsh -c "ls -l" -c "cd &i2c0" -i
   dtsh (0.2.1): A Devicetree Shell
   How to exit: q, or quit, or exit, or press Ctrl-D

   > Name              Labels          Binding
   ───────────────────────────────────────────────────────
   chosen
   aliases
   soc
   pin-controller    pinctrl         nordic,nrf-pinctrl
   entropy_bt_hci    rng_hci         zephyr,bt-hci-entropy
   sw-pwm            sw_pwm          nordic,nrf-sw-pwm
   cpus
   leds                              gpio-leds
   pwmleds                           pwm-leds
   buttons                           gpio-keys
   connector         arduino_header  arduino-header-r3
   analog-connector  arduino_adc     arduino,uno-adc

   /soc/i2c@40003000
   ❭


.. _dtsh-configuration:

Configuration
*************

Users can tweak DTSh appearance and behavior by overriding its defaults in configuration files:

- ``dtsh.ini``: to override global preferences (see :ref:`dtsh-preferences`)
- ``theme.ini``: to override styles and colors (see :ref:`dtsh-themes`)

These (optional) files must be located in a platform-dependent directory,
e.g. ``~/.config/dtsh`` on GNU/Linux systems.

Running ``dtsh`` with the ``-u --user-files`` option will initialize configuration templates
in the expected location:

.. code-block:: none

  $ dtsh -u
  User preferences: ~/.config/dtsh/dtsh.ini
  User theme: ~/.config/dtsh/theme.ini

.. tip::

   DTSh won't override a user file that already exists: manually remove the file(s),
   and run the command again.

Eventually:

- the ``--preferences FILE`` option permits to specify an additional preferences file to load
- the ``--theme FILE`` option permits to specify an additional theme file to load


.. _dtsh-first-steps:

First Steps
***********

The few examples bellow introduce the basics of DTSh.
Please refer to the :ref:`handbook <dtsh-handbook>` for complete documentation.

Navigate the devicetree like a file-system with `cd`:

.. code-block:: none

   /
   > cd &i2c0

   /soc/i2c@40003000
   > cd ../flash-controller@4001e000

   /soc/flash-controller@4001e000
   > cd

   /
   ❭


Print information about nodes with `ls`:

.. code-block:: none

   /
   > ls
   chosen
   aliases
   soc
   pin-controller
   entropy_bt_hci
   sw-pwm
   cpus
   leds
   pwmleds
   buttons
   connector
   analog-connector

   /
   > ls &flash0 -l
    Name        Labels  Binding
    ────────────────────────────────────
    partitions          fixed-partitions

   /
   > ls &flash0 -ld
    Name     Labels  Binding
    ─────────────────────────────
    flash@0  flash0  soc-nv-flash

   /
   > ls soc/flash-controller@4001e000/flash@0/partitions --format NKr
    Name             Also Known As               Registers
    ─────────────────────────────────────────────────────────────
    partition@0      mcuboot, boot_partition     0x0 (48 kB)
    partition@c000   image-0, slot0_partition    0xc000 (472 kB)
    partition@82000  image-1, slot1_partition    0x82000 (472 kB)
    partition@f8000  storage, storage_partition  0xf8000 (32 kB)


Visualize the devicetree with, well, `tree`:

.. code-block:: none

   /soc
   > tree --format Nc
                                      Compatible
                                      ────────────────────────────────────────────────────────────
   soc                                nordic,nrf52840-qiaa nordic,nrf52840 nordic,nrf52 simple-bus
   ├── interrupt-controller@e000e100  arm,v7m-nvic
   ├── timer@e000e010                 arm,armv7m-systick
   ├── ficr@10000000                  nordic,nrf-ficr
   ├── uicr@10001000                  nordic,nrf-uicr
   ├── memory@20000000                mmio-sram
   ├── clock@40000000                 nordic,nrf-clock
   ├── power@40000000                 nordic,nrf-power
   │   ├── gpregret1@4000051c         nordic,nrf-gpregret
   │   └── gpregret2@40000520         nordic,nrf-gpregret
   ├── radio@40001000                 nordic,nrf-radio
   │   └── ieee802154                 nordic,nrf-ieee802154
   ├── uart@40002000                  nordic,nrf-uarte
   ├── i2c@40003000                   nordic,nrf-twi
   │   └── bme680@76                  bosch,bme680


Search the devicetree with `find`:

.. code-block:: none

   /
   > find --with-description "2.4 GHz" -T --format NKCd
                           Also Known As  Binding           Description
                           ────────────────────────────────────────────────────────────────────
   /                       …              …                 …
   └── soc                 …              …                 …
       └── radio@40001000  radio          nordic,nrf-radio  Nordic nRF family RADIO peripheral…


*Export* the devicetree to HTML by redirecting (``>``) commands output:

.. code-block:: none

   /
   > ls -lR > board.html


.. include:: bib.rst

.. meta::
   :keywords: zephyr, devicetree, dts, viewer, user interface
