Muffin Peewee
#############

.. _description:

**muffin-peewee** -- Peewee_ ORM integration to Muffin_ framework.

.. _badges:

.. image:: https://github.com/klen/muffin-peewee/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-peewee/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-peewee
    :target: https://pypi.org/project/muffin-peewee/
    :alt: PYPI Version

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.7

.. _installation:

Installation
=============

**Muffin Peewee** should be installed using pip: ::

    pip install muffin-peewee

Optionally you are able to install it with postgresql drivers: ::

    pip install muffin-peewee[postgres]

.. _usage:

Usage
=====

.. code-block:: python

    from muffin import Application
    from muffin_peewee import Plugin as Peewee

    # Create Muffin Application
    app = Application('example')

    # Initialize the plugin
    # As alternative: jinja2 = Jinja2(app, **options)
    db = Peewee()
    db.init(app, PEEWEE_CONNECTION='postgres+pool+async://postgres:postgres@localhost:5432/database')


Options
-------

Format: ``Name`` -- Description (``default value``)

``CONNECTION`` -- connection string to your database (``sqlite:///db.sqlite``)

``CONNECTION_PARAMS`` -- Additional params for connection (``{}``)

``MANAGE_CONNECTIONS`` -- Install a middleware to manage db connections automatically (``True``)

``MIGRATIONS_ENABLED`` -- Enable migrations with ``peewee-migrate`` (``True``)

``MIGRATIONS_PATH`` -- Set path to the migrations folder (``migrations``)

Queries
-------

::

    @db.register
    class Test(peewee.Model):
        data = peewee.CharField()


    @app.route('/')
    async def view(request):
        return [t.data for t in Test.select()]

Manage connections
------------------
::

    # Set configuration option `MANAGE_CONNECTIONS` to False

    # Use context manager
    @app.route('/')
    async def view(request):
        async with db:
            # Work with db
            # ...


Migrations
----------

Create migrations: ::

    $ muffin example:app pw_create [NAME] [--auto]


Run migrations: ::

    $ muffin example:app pw_migrate [NAME] [--fake]


Rollback migrations: ::

    $ muffin example:app pw_rollback [NAME]


List migrations: ::

    $ muffin example:app pw_list


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
========

Licensed under a `MIT license`_.

.. _links:

.. _MIT license: http://opensource.org/licenses/MIT
.. _Muffin: https://github.com/klen/muffin
.. _Peewee: http://docs.peewee-orm.com/en/latest/
.. _klen: https://github.com/klen
