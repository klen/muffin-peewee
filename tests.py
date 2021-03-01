import muffin
import peewee
import pytest


@pytest.fixture
def app():
    return muffin.Application(
        'peewee', PEEWEE_CONNECTION='sqliteext+async:///:memory:'
    )


@pytest.fixture
def db(app):
    import muffin_peewee

    return muffin_peewee.Plugin(app)


@pytest.fixture(autouse=True)
def transaction(db):
    """Clean changes after test."""
    try:
        with db.database.atomic() as trans:
            yield True
            trans.rollback()
    except Exception:
        pass


def test_json_field(db):
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


def test_migrations(db, tmpdir):
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


def test_uuid(db):
    """ Test for UUID in Sqlite. """
    @db.register
    class M(peewee.Model):
        data = peewee.UUIDField()
    M.create_table()

    import uuid
    m = M(data=uuid.uuid1())
    m.save()

    assert M.get() == m


def test_cli(app):
    assert 'pw_create' in app.manage.commands
    assert 'pw_migrate' in app.manage.commands
    assert 'pw_rollback' in app.manage.commands
    assert 'pw_list' in app.manage.commands


async def test_async():
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

    async with db:
        assert db.transaction_depth() == 1

    assert db.transaction_depth() == 0


async def test_sync():
    import muffin_peewee

    app = muffin.Application('peewee', PEEWEE_CONNECTION='sqlite:///:memory:')
    muffin_peewee.Plugin(app)
    await app.lifespan.run('startup')
    await app.lifespan.run('shutdown')
