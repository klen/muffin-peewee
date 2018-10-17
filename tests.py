import muffin
import peewee
import pytest


@pytest.fixture(scope='session')
def app():
    return muffin.Application(
        'peewee',
        PLUGINS=['muffin_peewee'],
        PEEWEE_CONNECTION='sqliteext:///:memory:'
    )


@pytest.fixture(scope='session')
def model(app):
    from muffin_peewee.fields import JSONField

    @app.ps.peewee.register
    class Test(app.ps.peewee.TModel):
        data = peewee.CharField()
        json = JSONField(default={})

    try:
        Test.create_table()
    except peewee.OperationalError:
        pass

    return Test


@pytest.yield_fixture(autouse=True)
def transaction(app):
    """Clean changes after test."""
    try:
        with app.ps.peewee.database.atomic() as trans:
                yield True
                trans.rollback()
    except Exception:
        pass


def test_peewee(app, model):
    assert app.ps.peewee

    with pytest.raises(ValueError):
        model.post_save.connect(None)

    @model.post_save
    def test_signal(instance, created=False):
        instance.saved = getattr(instance, 'saved', 0) + 1

    ins = model(data='some', json={'key': 'value'})
    ins.save()

    assert ins.pk == ins.id
    assert ins.json
    assert ins.created
    assert ins.saved == 1

    ins.save()
    assert ins.saved == 2

    model.post_save.disconnect(test_signal)
    ins.save()
    assert ins.saved == 2

    with pytest.raises(ValueError):
        model.post_save.disconnect(test_signal)

    test = model.get()
    assert test.json == {'key': 'value'}

    assert ins.simple
    assert ins.to_simple(only=('id', 'data')) == {'data': 'some', 'id': 1}


def test_migrations(app, tmpdir):
    assert app.ps.peewee.router

    router = app.ps.peewee.router
    router.migrate_dir = str(tmpdir.mkdir('migrations'))

    assert not router.todo
    assert not router.done
    assert not router.diff

    # Create migration
    name = router.create('test')
    assert '001_test' == name
    assert router.todo
    assert not router.done
    assert router.diff

    # Run migrations
    router.run()
    assert router.done
    assert not router.diff

    name = router.create()
    assert '002_auto' == name


def test_uuid(app):
    """ Test for UUID in Sqlite. """
    @app.ps.peewee.register
    class M(app.ps.peewee.TModel):
        data = peewee.UUIDField()
    M.create_table()

    import uuid
    m = M(data=uuid.uuid1())
    m.save()

    assert M.get() == m


async def test_async_peewee(model):
    app = muffin.Application(
        'peewee',
        PLUGINS=['muffin_peewee'],
        PEEWEE_CONNECTION='sqliteext:///:memory:'
    )
    app.ps.peewee.startup(app)

    conn = await app.ps.peewee.database.async_connect()
    assert conn
    assert conn.cursor()
    await app.ps.peewee.database.async_close()

    with pytest.raises(Exception):
        conn.cursor()

    assert app.ps.peewee.database.obj.execution_context_depth() == 0

    with (await app.ps.peewee.manage()):
        assert app.ps.peewee.database.obj.execution_context_depth() == 1
        model.create_table()
        model.select().execute()

    assert app.ps.peewee.database.obj.execution_context_depth() == 0
