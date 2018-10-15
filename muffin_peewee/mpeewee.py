"""Manage database connections asyncrounosly."""

import asyncio
import collections
import threading
import logging

import peewee as pw
from playhouse.db_url import schemes, SqliteExtDatabase, connect # noqa
from playhouse.pool import PooledDatabase, PooledMySQLDatabase, PooledPostgresqlDatabase


logger = logging.getLogger('peewee')

pw.SqliteDatabase.field_types['UUID'] = 'UUID'


CONN_PARAMS = {
    'autocommit': lambda: None,
    'closed': lambda: True,
    'conn': lambda: None,
    'context_stack': lambda: [],
    'transactions': lambda: [],
}


LOCAL = threading.local()
METHODS = set([
    '__setattr__', '__getattr__', '__delattr__', '__current__', 'reset', 'set_connection'])


class ConnectionLocal(pw._ConnectionState):

    """Keep connection info.

    While asyncio loop is running the object is local to current running task,
    otherwise is local to current thread.

    """

    def __getattribute__(self, name):
        """Get attribute from current task's space."""
        if name in METHODS:
            return object.__getattribute__(self, name)

        try:
            return getattr(self.__current__, name)

        except AttributeError:
            if name not in CONN_PARAMS:
                raise

            default = CONN_PARAMS[name]()
            setattr(self, name, default)

            return default

    def __setattr__(self, name, value):
        """Set attribute to current space."""
        self.__current__.__dict__[name] = value

    def __delattr__(self, name):
        """Delete attribute from current space."""
        delattr(self.__current__, name)

    @property
    def __current__(self):
        """Create namespace inside running task."""
        loop = asyncio.get_event_loop()
        if not loop or not loop.is_running():
            return LOCAL

        task = asyncio.Task.current_task(loop=loop)
        if not task:
            raise RuntimeError('No task is currently running')

        if not hasattr(task, '_locals'):
            task._locals = lambda: None

        return task._locals


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
        except pw.DatabaseError:
            self._db.rollback()

        finally:
            if not self._db.is_closed():
                self._db.close()
            self._db = None


class AIODatabase:

    """Support for async operations."""

    _aioconn_lock = None

    def async_init(self, loop=None):
        """Use when application is starting."""
        self._loop = loop or asyncio.get_event_loop()
        self._aioconn_lock = asyncio.Lock(loop=loop)

        # FIX: SQLITE in memory database
        if not self.database == ':memory:':
            self._state = ConnectionLocal()

    @asyncio.coroutine
    def async_connect(self):
        """Catch a connection asyncrounosly."""
        if self._aioconn_lock is None:
            raise Exception('Error, database not properly initialized before async connection')

        with (yield from self._aioconn_lock):
            self.connect(True)
        return self._state.conn

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
        """Wait for connection from pool."""
        if self._waiters is None:
            raise Exception('Error, database not properly initialized before async connection')

        if self._waiters or self.max_connections and (len(self._in_use) >= self.max_connections):
            fut = asyncio.Future(loop=self._loop)
            self._waiters.append(fut)

            try:
                logger.debug('Wait for connection.')
                yield from fut
            finally:
                self._waiters.remove(fut)

        self.connect()
        return self._state.conn

    def _close(self, *args, **kwargs):
        """Release a waiter."""
        super(PooledAIODatabase, self)._close(*args, **kwargs)
        for waiter in self._waiters:
            if not waiter.done():
                logger.debug('Leave a waiter.')
                waiter.set_result(True)
                break


schemes['sqlite'] = type(
    'AIOSqliteDatabase', (AIODatabase, pw.SqliteDatabase), {})

schemes['sqlite+pool'] = type(
    'AIOPooledSqliteDatabase', (PooledAIODatabase, PooledDatabase, schemes['sqlite']), {})

schemes['sqliteext'] = type(
    'AIOSqliteExtDatabase', (AIODatabase, SqliteExtDatabase), {})

schemes['sqliteext+pool'] = type(
    'AIOPooledSqliteExtDatabase', (PooledAIODatabase, PooledDatabase, schemes['sqliteext']), {})

schemes['mysql'] = type(
    'AIOMySQLDatabase', (AIODatabase, pw.MySQLDatabase), {})

schemes['mysql+pool'] = type(
    'AIOPooledMySQLDatabase', (PooledAIODatabase, PooledMySQLDatabase, schemes['mysql']), {})

schemes['postgres'] = schemes['postgresql'] = type(
    'AIOPostgresqlDatabase', (AIODatabase, pw.PostgresqlDatabase), {})

schemes['postgres+pool'] = schemes['postgresql+pool'] = type(
    'AIOPooledPostgresqlDatabase',
    (PooledAIODatabase, PooledPostgresqlDatabase, schemes['postgres']), {})

try:
    from playhouse.db_url import PostgresqlExtDatabase, PooledPostgresqlExtDatabase

    schemes['postgresext'] = schemes['postgresqlext'] = type(
        'AIOPostgresqlExtDatabase', (AIODatabase, PostgresqlExtDatabase), {})

    schemes['postgresext+pool'] = schemes['postgresqlext+pool'] = type(
        'AIOPooledPostgresqlExtDatabase',
        (PooledAIODatabase, PooledPostgresqlExtDatabase, schemes['postgres']), {})

except ImportError:
    pass
