====
dtsh
====

:Author: Chris Duf

**dtsh** is a *shell-like* interface to the devicetree models produced
by the ``dtlib`` and ``edtlib`` libraries now maintained as parts of the
Zephyr project
(`python-devicetree <https://github.com/zephyrproject-rtos/python-devicetree>`__),
and also available as independent Python packages via
`PyPI <https://pypi.org/project/devicetree/>`__.

Once a devicetree model is loaded from its DT sources and bindings,
``dtsh`` will show:

-  a file-system metaphor mapped to devicetree `path
   names <https://devicetree-specification.readthedocs.io/en/stable/devicetree-basics.html#path-names>`__
-  common commands (for e.g. ``ls``) and option (for e.g. ``-l``) syntax
   compatible with GNU getopt
-  `GNU
   readline <https://tiswww.cwru.edu/php/chet/readline/rltop.html>`__
   integration for commands history, auto-completion, and well-known key
   bindings
-  a *rich* user interface (`Python
   rich <https://pypi.org/project/rich>`__)

This tool was created to explore Zephyr's
`devicetree <https://docs.zephyrproject.org/latest/build/dts/intro.html>`__
and
`bindings <https://docs.zephyrproject.org/latest/build/dts/bindings.html>`__.

   ☂ **DISCLAMER**: This software is a Proof of Concept, something like
   a Request For Comments, about:

   -  the usefulness of this kind of tool, to which audience
   -  the command line approach's ergonomics
   -  which shell commands are the most useful (my personal preference
      may go to ``ls -lR --pager /``)
   -  which commands are missing that would definitely be worth
      implementing
   -  the software compatibility with Linux devicetrees (for e.g. when
      building the Linux kernel for ARM architectures)
   -  the `BUGS <https://github.com/dottspina/dtsh/issues>`__ ;-)

   This software is developed and tested on Fedora Workstation: should
   work more or less Out Of The Box™ on most modern Linux distributions,
   mileage may vary on other platforms.

Quick start
===========

Install in *current Python environment*:

::

   $ git clone https://github.com/dottspina/dtsh.git
   $ cd dtsh
   $ pip install .

The ``dtsh`` command should now be available.

To start a shell session: ``dtsh [<dts-file>] [<binding-dir>*]``

Where:

-  ``<dts-file>``: Path to a device tree source file (``.dts``); if
   unspecified, defaults to ``$PWD/build/zephyr/zephyr.dts``
-  ``<binding-dirs>``: List of path to search for DT bindings
   (``.yaml``); if unspecified, and the environment variable
   ``ZEPHYR_BASE`` is set, defaults to Zephyr's DT bindings

At the shell prompt, issue the ``man dtsh`` command to access the most
up-to-date documentation.

An `introductory video <https://youtu.be/pc2AMx1iPPE>`__ is also
available (Youtube).

Requirements
------------

Most ``dtsh`` requirements are Python dependencies, that should install
automatically.

Beside these, a terminal with 256 colors support, and a font with a
reasonable unicode characters set (arrows, lines, simple symbols) are
recommended.

Most of ``dtsh`` user interface's styles can be customized by creating a
*theme* file ``$DTSH_CONFIG_DIR/theme`` (see *Theme* in ``man dtsh``).

Examples
--------

To open an arbitrary DT source file, with custom bindings:

::

   $ dtsh /path/to/foobar.dts /path/to/custom/bindings /path/to/other/custom/bindings

To open a DT source file with Zephyr's bindings (``$ZEPHYR_BASE/boards``
and ``$ZEPHYR_BASE/dts/bindings``):

::

   $ export ZEPHYR_BASE=/path/to/zephyr
   $ dtsh /path/to/foobar.dts

To *fast-open* the current Zephyr project's devicetree
(``$PWD/build/zephyr/zephyr.dts``), assuming ``ZEPHYR_BASE`` is set:

::

   $ cd /path/to/some/zephyr/project
   $ dtsh

Zephyr tips
-----------

It's recommended to
`install <https://docs.zephyrproject.org/latest/develop/getting_started/index.html#get-zephyr-and-install-python-dependencies>`__
the Zephyr's
`west <https://docs.zephyrproject.org/latest/develop/west/index.html>`__
workspace into a dedicated Python virtual environment.

``dtsh`` can be safely installed into this same environment.

Once this workspace is activated (e.g. by sourcing
``$ZEPHYR_BASE/zephyr-env.sh``), this simple workflow should work:

::

   $ cd /path/to/some/zephyr/project
   $ west build
   $ dtsh

Development
===========

Virtual environment
-------------------

Install ``dtsh`` in a dedicated virtual environment for *hacking*:

.. code:: bash

   git clone https://github.com/dottspina/dtsh.git
   cd dtsh
   # for Python 3.9 and above
   python -m venv --upgrade-deps .venv
   . .venv/bin/activate
   # for Python 3.7 and 3.8
   python -m venv .venv
   . .venv/bin/activate
   pip install --upgrade pip setuptools
   # pip will prefer wheels when installing from PyPI
   pip install wheel
   # install dtsh in development mode
   pip install --editable .

Tests
-----

To run the unit tests:

.. code:: bash

   cd dtsh
   . .venv/bin/activate
   # install test requirements
   pip install ".[test]"
   # run unit tests
   pytest tests

Contributing
------------

Though Python is not my mother's thong, I've tried to keep some basic
design principles, and hacking the source code should prove straight
forward:

-  to define a new built-in command: look for the ``DtshCommand`` and
   ``DtshCommandOption`` classes into the
   `dtsh.dtsh <https://github.com/dottspina/dtsh/blob/main/src/dtsh/dtsh.py>`__
   module, copy an existing command (for e.g.
   `ls <https://github.com/dottspina/dtsh/blob/main/src/dtsh/builtin_ls.py>`__)
   as a template, and customize it
-  re-use helpers and views in the
   `dtsh.tui <https://github.com/dottspina/dtsh/blob/main/src/dtsh/tui.py>`__
   module to build command outputs

Propose any contribution (documentation, bug fix, new features, code
review) as a `pull request <https://github.com/dottspina/dtsh/pulls>`__.
