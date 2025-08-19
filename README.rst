Brazilian Pix for pretix - integration with OpenPix
===================================================

This is a plugin for `pretix`_. to allow the use of Brazilian Pix payment method 
integrated with an `OpenPix`_ account.

**You must have an active OpenPix account to be able to receive payments with this plugin**

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in the 'plugins' tab in the settings.

Linter and formatters
---------------------

This plugin has a pre-commit hook configuration that checks and enforces some
code style rules. To install it locally, you need to install `pre-commit` 
package and install the hooks::

    pip install pre-commit
    pre-commit install

To check manually for rule violations, run::

    pre-commit run -a

When you have these hooks installed, you will not be allowed to commit code that
doesn't follow the rules.

These rules are also enforced in CI.

Releasing new version
---------------------

To create a new release you need to have `bumpver`_ installed::

    pip install bumpver

The projet is versioned using the pattern `major.minor.patch` 
(`--major`, `--minor` and `--patch`). Use the desired flag before running it::

    bumpver update --minor

This command will update all version references, commit it and create
a tag for that release. You can use `--dry` to check what will be updated
without commiting it.

License
-------

Copyright 2025 Renne Rocha

Released under the terms of the AGPL

.. _bumpver: https://github.com/mbarkhau/bumpver
.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
.. _OpenPix: https://openpix.com.br