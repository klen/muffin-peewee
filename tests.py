import sys
from unittest import mock

import muffin
import peewee
import pytest


@pytest.fixture
def app():
    return muffin.Application(peewee_connection='sqliteext+async:///:memory:')


@pytest.fixture
def db(app):
    import muffin_peewee

    return muffin_peewee.Plugin(app)


@pytest.fixture
def transaction(db):
    """Clean changes after test."""
    try:
        with db.database.atomic() as trans:
            yield True
            trans.rollback()
    except Exception:
        pass


def test_json_field(db, transaction):
    from muffin_peewee import JSONField

    @db.register
    class Test(peewee.Model):
        data = peewee.CharField()
        json = JSONField(default={})

    Test.create_table()

    ins = Test(data='some', json={'key': 'value'})
    ins.save()

    assert ins.json

    test = Test.get()
    assert test.json == {'key': 'value'}


def test_migrations(db, tmpdir, transaction):
    assert db.router

    db.router.migrate_dir = str(tmpdir.mkdir('migrations'))

    assert not db.router.todo
    assert not db.router.done
    assert not db.router.diff

    # Create migration
    name = db.router.create('test')
    assert '001_test' == name
    assert db.router.todo
    assert not db.router.done
    assert db.router.diff

    # Run migrations
    db.router.run()
    assert db.router.done
    assert not db.router.diff

    name = db.router.create()
    assert '002_auto' == name


def test_uuid(db, transaction):
    """ Test for UUID in Sqlite. """
    @db.register
    class M(peewee.Model):
        data = peewee.UUIDField()
    M.create_table()

    import uuid
    m = M(data=uuid.uuid1())
    m.save()

    assert M.get() == m


def test_cli(app, db):
    assert 'pw_create' in app.manage.commands
    assert 'pw_migrate' in app.manage.commands
    assert 'pw_rollback' in app.manage.commands
    assert 'pw_list' in app.manage.commands


async def test_async(transaction):
    import muffin_peewee

    app = muffin.Application('peewee', PEEWEE_CONNECTION='sqliteext+async:///:memory:')
    db = muffin_peewee.Plugin(app)

    conn = await db.connect_async()
    assert conn
    assert conn.cursor()
    db.close()

    with pytest.raises(Exception):
        conn.cursor()

    assert db.transaction_depth() == 0

    @db.register
    class Test(peewee.Model):
        value = peewee.CharField()

    Test.create_table()
    assert list(Test.select().execute()) == []
    db.close()

    async with db as conn:
        assert conn
        assert db.transaction_depth() == 1

    assert db.transaction_depth() == 0


async def test_sync():
    import muffin_peewee

    app = muffin.Application('peewee', PEEWEE_CONNECTION='sqlite+async:///:memory:')
    db = muffin_peewee.Plugin(app)
    with mock.patch.object(db.database.obj, 'close_async') as mocked:
        await app.lifespan.run('startup')
        await app.lifespan.run('shutdown')
        assert mocked.called
        # TODO: py37
        if sys.version_info >= (3, 8):
            assert mocked.await_count == 1


async def test_sync_middleware(tmp_path):
    from muffin_peewee import Plugin

    db = tmp_path / 'db.sqlite'
    app = muffin.Application('peewee', PEEWEE_CONNECTION=f"sqlite:///{db}")
    db = Plugin(app)

    assert app.internal_middlewares

    @db.register
    class User(peewee.Model):
        name = peewee.CharField()

    User.create_table()
    User.create(name='test')

    @app.route('/')
    async def index(request):
        return User.select().count()

    client = muffin.TestClient(app)
    async with client.lifespan():
        res = await client.get('/')
        assert res.status_code == 200
        assert await res.text() == '1'


async def test_async_middleware(tmp_path):
    from muffin_peewee import Plugin

    db = tmp_path / 'db.sqlite'
    app = muffin.Application('peewee', PEEWEE_CONNECTION=f"sqlite+async:///{db}")
    db = Plugin(app)

    assert app.internal_middlewares

    @db.register
    class User(peewee.Model):
        name = peewee.CharField()

    User.create_table()
    User.create(name='test')

    @app.route('/')
    async def index(request):
        return User.select().count()

    client = muffin.TestClient(app)
    async with client.lifespan():
        res = await client.get('/')
        assert res.status_code == 200
        assert await res.text() == '1'
