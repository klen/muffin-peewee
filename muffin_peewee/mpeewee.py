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


THREADING_LOCAL = threading.local()
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
            return THREADING_LOCAL

        task = asyncio.Task.current_task(loop=loop)
        if not task:
            raise RuntimeError('No task is currently running')

        if not hasattr(task, '_locals'):
            task._locals = lambda: None

        return task._locals


class AIODatabase:

    """Support for async operations."""

    _async_lock = None

    def init_async(self, loop=None):
        """Use when application is starting."""
        self._loop = loop or asyncio.get_event_loop()
        self._async_lock = asyncio.Lock(loop=loop)

        # FIX: SQLITE in memory database
        if not self.database == ':memory:':
            self._state = ConnectionLocal()

    async def async_connect(self):
        """Catch a connection asyncrounosly."""
        if self._async_lock is None:
            raise Exception('Error, database not properly initialized before async connection')

        async with self._async_lock:
            self.connect(True)

        return self._state.conn

    async def async_close(self):
        """Close the current connection asyncrounosly."""
        if self._async_lock is None:
            raise Exception('Error, database not properly initialized before async connection')

        async with self._async_lock:
            self.close()


class PooledAIODatabase:

    """Async pool."""

    _waiters = None

    def init_async(self, loop):
        """Initialize self."""
        super(PooledAIODatabase, self).init_async(loop)
        self._waiters = collections.deque()

    async def async_connect(self):
        """Asyncronously wait for a connection from the pool."""
        if self._waiters is None:
            raise Exception('Error, database not properly initialized before async connection')

        if self._waiters or self.max_connections and (len(self._in_use) >= self.max_connections):
            waiter = asyncio.Future(loop=self._loop)
            self._waiters.append(waiter)

            try:
                logger.debug('Wait for connection.')
                await waiter
            finally:
                self._waiters.remove(waiter)

        self.connect()
        return self._state.conn

    def _close(self, conn):
        """Release waiters."""
        super(PooledAIODatabase, self)._close(conn)
        for waiter in self._waiters:
            if not waiter.done():
                logger.debug('Release a waiter')
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
