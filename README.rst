Muffin Peewee
#############

.. _description:

Muffin Peewee -- Peewee ORM integration to Muffin framework.

.. _badges:

.. image:: http://img.shields.io/travis/klen/muffin-peewee.svg?style=flat-square
    :target: http://travis-ci.org/klen/muffin-peewee
    :alt: Build Status

.. image:: http://img.shields.io/pypi/v/muffin-peewee.svg?style=flat-square
    :target: https://pypi.python.org/pypi/muffin-peewee

.. image:: http://img.shields.io/pypi/dm/muffin-peewee.svg?style=flat-square
    :target: https://pypi.python.org/pypi/muffin-peewee

.. image:: http://img.shields.io/gratipay/klen.svg?style=flat-square
    :target: https://www.gratipay.com/klen/
    :alt: Donate

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.3

.. _installation:

Installation
=============

**Muffin Peewee** should be installed using pip: ::

    pip install muffin-peewee

.. _usage:

Usage
=====

Add `muffin_peewee` to `PLUGINS` in your Muffin Application configuration.

Options
-------

`PEEWEE_CONNECTION` -- connection string to your database (sqlite:///db.sqlite)

`PEEWEE_CONNECTION_MANUAL` -- Control db connection manually

`PEEWEE_CONNECTION_PARAMS` -- Additional params for connection ({})

`PEEWEE_MIGRATIONS_ENABLED` -- enable migrations (True)

`PEEWEE_MIGRATIONS_PATH` -- path to migration folder (migrations)

Queries
-------

::

    @app.ps.peewee.register
    class Test(peewee.Model):
        data = peewee.CharField()


    @app.register
    def view(request):
        return [t.data for t in Test.select()]

Manage connections
------------------
::

    # Set configuration option `PEEWEE_CONNECTION_MANUAL` to True

    # Use context manager
    @app.register
    def view(request):
        with app.ps.peewee.manage() as conn:
            # Work with db
            # ...


Migrations
----------

Create migrations: ::

    $ muffin example:app create [NAME]


Run migrations: ::

    $ muffin example:app migrate [NAME]

Load/Dump data to CSV
---------------------

Dump table `test` to CSV file: ::

    $ muffin example:app csv_dump test


Load data from CSV file to table `test`: ::

    $ muffin example:app csv_load test


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/muffin-peewee/issues

.. _contributing:

Contributing
============

Development of Muffin Peewee happens at: https://github.com/klen/muffin-peewee


Contributors
=============

* klen_ (Kirill Klenov)

.. _license:

License
=======

Licensed under a `MIT license`_.

.. _links:

.. _MIT license: http://opensource.org/licenses/MIT
.. _klen: https://github.com/klen
