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

.. image:: https://img.shields.io/pypi/pyversions/muffin-peewee
    :target: https://pypi.org/project/muffin-peewee/
    :alt: Python Versions

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
    db.setup(app, PEEWEE_CONNECTION='postgres+pool+async://postgres:postgres@localhost:5432/database')


Options
-------

=========================== ======================================= =========================== 
Name                        Default value                           Desctiption
--------------------------- --------------------------------------- ---------------------------
**CONNECTION**              ``sqlite+async:///db.sqlite``           Database URL
**CONNECTION_PARAMS**       ``{}``                                  Additional params for DB connection
**MANAGE_CONNECTIONS**      ``True``                                Install a middleware to aquire db connections automatically
**MIGRATIONS_ENABLED**      ``True``                                Enable migrations with
**MIGRATIONS_PATH**         ``"migrations"``                        Set path to the migrations folder
=========================== ======================================= =========================== 

You are able to provide the options when you are initiliazing the plugin:

.. code-block:: python

    db.setup(app, connection='DB_URL')


Or setup it inside ``Muffin.Application`` config using the ``PEEWEE_`` prefix:

.. code-block:: python

   PEEWEE_CONNECTION = 'DB_URL'

``Muffin.Application`` configuration options are case insensitive

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
