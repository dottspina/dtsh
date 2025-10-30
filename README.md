# DTSh - Zephyr External project/module

Integrating the Devicetree Shell into Zephyr as a West extension provided by an *external project*.
The project is also a *module* to benefit from the `west packages` commodity.

If you don't know what DTSh is, take a look at its [Handbook].

## Installation

To install this project, you will need to define your own manifest file, or pull it in by adding a submanifest. See [External Projects/Modules] for more information.

E.g. assuming the same paths as in [Zephyr Getting Started Guide], create `zephyrproject/zephyr/submanifests/dtsh.yaml` with the following content:

``` yaml
manifest:
  projects:
    - name: dtsh
      url: https://github.com/dottspina/dtsh.git
      revision: zephyr
      path: modules/tools/dtsh
      west-commands: scripts/west-commands.yml
```

Then update the workspace and install DTSh requirements:

``` sh
west update dtsh
west packages -m dtsh pip --install 
```

> [!NOTE]
> 
> `west update dtsh` will fetch all tags from the [DTSh project]: ignore them, they don't point to versions of this Zephyr module, and are entirely irrelevant here.  

## West command 

Once installed, this project/module should provide the `west dtsh` command.

```
$ west dtsh --help
usage: west dtsh [-h] [-b DIR] [-u] [--preferences FILE] [--theme FILE] [-c CMD] [-f FILE] [-i] [DTS]

Interactive DTS file viewer with a shell-like command line interface:
- easily navigate and visualize the devicetree
- find nodes based on e.g. supported bus protocols, bindings, generated IRQs,
  memory size, or keywords like 'sensor' or 'PWM'
- redirect commands output to files (text, HTML, SVG)
  to document hardware configurations or simply take notes
- scriptable (aka batch modes)
- contextual auto-completion, commands history, semantic highlighting, user profiles

Handbook: https://dottspina.github.io/dtsh/handbook.html

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
```

> [!NOTE]
> 
> It's recommended to install the module to its default location, `modules/tools/dtsh`.
> Otherwise, be sure to set the `ZEPHYR_BASE` environment variable before running `west dtsh`.

West command completion scripts are provided for [bash](etc/west-completion.bash) and [zsh](etc/west-completion.zsh), e.g.:

``` sh
source etc/west-completion.bash
```

[External Projects/Modules]: https://docs.zephyrproject.org/latest/develop/manifest/index.html#external-projects-modules
[Handbook]: https://dottspina.github.io/dtsh/handbook.html
[Zephyr Getting Started Guide]: https://docs.zephyrproject.org/latest/develop/getting_started/
[DTSh project]: https://github.com/dottspina/dtsh
