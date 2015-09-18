"""Manage database connections asyncrounosly."""

import asyncio
import collections

import peewee
from muffin.utils import slocal
from playhouse.db_url import parseresult_to_dict, urlparse, schemes
from playhouse.pool import PooledDatabase, PooledMySQLDatabase, PooledPostgresqlDatabase


peewee.SqliteDatabase.register_fields({'uuid': 'UUID'})


CONN_PARAMS = {
    'autocommit': lambda: None,
    'closed': lambda: True,
    'conn': lambda: None,
    'context_stack': lambda: [],
    'transactions': lambda: [],
}


class _ConnectionTaskLocal(slocal):

    """Keep connection info.

    While asyncio loop is running the object is local to current running task,
    otherwise is local to current thread.

    """

    def __getattribute__(self, name):
        try:
            return super(_ConnectionTaskLocal, self).__getattribute__(name)
        except AttributeError:

            if name not in CONN_PARAMS:
                raise

            default = CONN_PARAMS[name]()
            setattr(self, name, default)

            return default


class _ContextManager:

    """Context manager.

    This enables the following idiom for acquiring and releasing a database around a block:

        with (yield from database):
            <block>
    """

    def __init__(self, db):
        self._db = db

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        try:
            self._db.commit()
        except peewee.DatabaseError:
            self._db.rollback()

        finally:
            if not self._db.is_closed():
                self._db.close()
            self._db = None


class AIODatabase:

    """Support for async operations."""

    _aioconn_lock = None

    def async_init(self, loop):
        """Used when application is starting."""
        self._loop = loop
        self._aioconn_lock = asyncio.Lock(loop=loop)

        # FIX: SQLITE in memory database
        if not self.database == ':memory:':
            self._Database__local = _ConnectionTaskLocal(loop=loop)

    @asyncio.coroutine
    def async_connect(self):
        """Catch a connection asyncrounosly."""
        if self._aioconn_lock is None:
            raise Exception('Error, database not properly initialized before async connection')

        with (yield from self._aioconn_lock):
            self.connect()
        return self._Database__local.conn

    @asyncio.coroutine
    def async_close(self):
        """Close the current connection asyncrounosly."""
        if self._aioconn_lock is None:
            raise Exception('Error, database not properly initialized before async connection')

        with (yield from self._aioconn_lock):
            self.close()


class PooledAIODatabase:

    """Async pool."""

    _waiters = None

    def async_init(self, loop):
        """Initialize self."""
        super(PooledAIODatabase, self).async_init(loop)
        self._waiters = collections.deque()

    @asyncio.coroutine
    def async_connect(self):
        """Async connection."""
        if self._waiters is None:
            raise Exception('Error, database not properly initialized before async connection')

        if self._waiters or self.max_connections and (len(self._in_use) >= self.max_connections):
            fut = asyncio.Future(loop=self._loop)
            self._waiters.append(fut)

            try:
                yield from fut
            finally:
                self._waiters.remove(fut)

        self.connect()
        return self._Database__local.conn

    def _close(self, *args, **kwargs):
        for waiter in self._waiters:
            if not waiter.done():
                waiter.set_result(True)
                break
        super(PooledAIODatabase, self)._close(*args, **kwargs)


schemes['sqlite'] = type('AIOSqliteDatabase', (AIODatabase, peewee.SqliteDatabase), {})
schemes['sqlite+pool'] = type(
    'AIOPooledSqliteDatabase', (PooledAIODatabase, PooledDatabase, schemes['sqlite']), {})

schemes['mysql'] = type('AIOMySQLDatabase', (AIODatabase, peewee.MySQLDatabase), {})
schemes['mysql+pool'] = type(
    'AIOPooledMySQLDatabase', (PooledAIODatabase, PooledMySQLDatabase, schemes['mysql']), {})

schemes['postgres'] = schemes['postgresql'] = type(
    'AIOPostgresqlDatabase', (AIODatabase, peewee.PostgresqlDatabase), {})
schemes['postgres+pool'] = schemes['postgresql+pool'] = type(
    'AIOPooledPostgresqlDatabase',
    (PooledAIODatabase, PooledPostgresqlDatabase, schemes['postgres']), {})


def connect(url, **connect_params):
    """Support async databases."""
    parsed = urlparse(url)
    connect_kwargs = parseresult_to_dict(parsed)
    connect_kwargs.update(connect_params)
    database_class = schemes.get(parsed.scheme)

    if database_class is None:
        if database_class in schemes:
            raise RuntimeError('Attempted to use "%s" but a required library '
                               'could not be imported.' % parsed.scheme)
        raise RuntimeError('Unrecognized or unsupported scheme: "%s".' % parsed.scheme)

    return database_class(**connect_kwargs)
