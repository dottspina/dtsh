.. _dtsh-tips:

FAQ & Tips
##########

Collection of FAQ and tips.


.. _dtsh-tips-dtsh:

Running DTSh
************


.. _dtsh-tips-dtsh-lacks-binding:

Failed to open devicetree, lacks bindings
=========================================

DTSh will most often rely on the CMake cache content to retrieve the *bindings search path*::

   build/
   ├── CMakeCache.txt
   └── zephyr/
       └── zephyr.dts

When DTSh can't find this cache file, and ``ZEPHYR_BASE`` is not set, the devicetree model initialization will fail::

  $ dtsh foobar.dts
  Failed to initialize devicetree:
  DTS error: interrupt controller <Node /soc/interrupt-controller@e000e100 in '/path/to/foobar.dts'> for <Node /soc/clock@40000000 in '/path/to/foobar.dts'> lacks binding

.. tip::

  Setting ``ZEPHYR_BASE`` will likely fix the initialization error::

    $ export ZEPHYR_BASE=/path/to/zephyr
    $ dtsh /path/to/foobar.dts

  For more complex use cases, refer to :ref:`dtsh-usage-others` in the Getting Started Guide.


.. _dtsh-tips-tui:

User interface
***************


.. _dtsh-tips-tui-prompt:

I'd prefer the traditional ``$`` prompt
=======================================

The default prompt is based on a Unicode symbol (``U+276D``):

- it may not render properly
- you may prefer a more traditional shell prompt like ``$``

.. tip::

   Create a user preferences file (see :ref:`dtsh-preferences`), and change the prompt string to your convenience::

     # Traditional user prompt: "$ ",
     # using $$ to escape the dollar sign:
     prompt.wchar = $$

     # Or to prevent confusion with the OS shell prompt,
     # e.g. "(dtsh)$ ":
     prompt.wchar = (dtsh)$$

   See also the other :ref:`preferences <dtsh-prefs-prompt>` that configure the prompt.


.. _dtsh-tips-tui-sober:

I'd prefer something a little more sober
========================================

DTSh use :ref:`themes <dtsh-prefs-prompt>` to consistently represent the different types of information: e.g. by default compatible strings are always green, and things that behave like *symbolic links* (e.g. aliases) are all italics

However, the default colors and styles:

- are heavily subjective, and may not be to your linking
- may not play well with desktop or terminal theme
- you can end up finding these *garish* colors tiring (we do)

.. tip::

  The `/etc/preferences <https://github.com/dottspina/dtsh/tree/dtsh-next/etc/preferences>`_ and `/etc/themes <https://github.com/dottspina/dtsh/tree/dtsh-next/etc/themes>`_ directories contain *sober* preferences and theme files.

  .. code-block:: none

    $ dtsh --preferences etc/preferences/sober.ini --theme etc/themes/sober.ini

  .. figure:: img/sober.png
     :align: center
     :alt: Something a little more sober
     :width: 100%

     Something a little more sober


.. _dtsh-tips-redi2:

Command output redirection
***************************


.. _dtsh-tips-html-backgrounds:

Mismatched HTML backgrounds
===========================

Default styles are intended for reading the commands output on the terminal, and my not play well when redirecting to HTML, e.g. producing disturbing mix of backgrounds:

.. list-table:: Default HTML rendering
   :widths: auto
   :align: center

   * - ``pref.html.theme``
     - ``html`` (light background)
   * - ``pref.yaml.theme``
     - ``monokai`` (dark background)
   * - ``pref.dts.theme``
     - ``monokai`` (dark background)


.. figure:: /img/html-ugly.png
  :align: center
  :alt: Mismatched HTML backgrounds

  Mismatched HTML backgrounds

.. tip::

  Create a user preferences file (see :ref:`dtsh-preferences`), and try to adjust involved themes to get a better backgrounds match, e.g. for an HTML file with *light* CSS styles::

    pref.html.theme = html
    pref.yaml.theme = bw
    pref.dts.theme = bw

  The `/etc/preferences <https://github.com/dottspina/dtsh/tree/dtsh-next/etc/preferences>`_ directory contains example preference files.


.. include:: bib.rst

.. meta::
   :keywords: zephyr, devicetree, dts, viewer, user interface
