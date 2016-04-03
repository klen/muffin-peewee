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

Or install it manually like this: ::

    db = muffin_peewee.Plugin(**{'options': 'here'})

    app = muffin.Application('test')
    app.install(db)


Options
-------

`PEEWEE_CONNECTION` -- connection string to your database (sqlite:///db.sqlite)

`PEEWEE_CONNECTION_PARAMS` -- Additional params for connection ({})

`PEEWEE_CONNECTION_MANUAL` -- Doesn't manage db connections automatically

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
        with (yield from app.ps.peewee.manage()):
            # Work with db
            # ...


Migrations
----------

Create migrations: ::

    $ muffin example:app create [NAME] [--auto]


Run migrations: ::

    $ muffin example:app migrate [NAME] [--fake]


Rollback migrations: ::

    $ muffin example:app rollback NAME


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

If you wish to express your appreciation for the project, you are welcome to send
a postcard to: ::

    Kirill Klenov
    pos. Severny 8-3
    MO, Istra, 143500
    Russia

.. _links:

.. _MIT license: http://opensource.org/licenses/MIT
.. _klen: https://github.com/klen
