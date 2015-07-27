import muffin
import peewee
import pytest


@pytest.fixture(scope='session')
def app(loop):
    return muffin.Application(
        'peewee', loop=loop,

        PLUGINS=['muffin_peewee'],
        PEEWEE_CONNECTION='sqlite:///:memory:')


@pytest.fixture(scope='session')
def model(app, loop):

    @app.ps.peewee.register
    class Test(app.ps.peewee.TModel):
        data = peewee.CharField()

    Test.create_table()
    return Test


def test_peewee(app, model):
    assert app.ps.peewee

    ins = model(data='some')
    ins.save()

    assert ins.pk == ins.id
    assert ins.created

    assert [d for d in model.select()]
    assert ins.simple
    assert ins.to_simple(only=('id', 'data')) == {'data': 'some', 'id': 1}


@pytest.mark.async
def test_async_peewee(app, model):
    conn = yield from app.ps.peewee.database.async_connect()
    assert conn
    assert conn.cursor()
    yield from app.ps.peewee.database.async_close()

    with pytest.raises(Exception):
        conn.cursor()

    assert app.ps.peewee.database.obj.execution_context_depth() == 0

    with (yield from app.ps.peewee.manage()):
        assert app.ps.peewee.database.obj.execution_context_depth() == 1
        model.create_table()
        model.select().execute()

    assert app.ps.peewee.database.obj.execution_context_depth() == 0


def test_migrations(app, tmpdir):
    assert app.ps.peewee.router

    router = app.ps.peewee.router
    router.migrate_dir = str(tmpdir.mkdir('migrations'))

    assert not router.fs_migrations
    assert not router.db_migrations
    assert not router.diff

    # Create migration
    path = router.create('test')
    assert '000_test.py' in path
    assert router.fs_migrations
    assert not router.db_migrations
    assert router.diff

    # Run migrations
    router.run()
    assert router.db_migrations
    assert not router.diff

    path = router.create()
    assert '001_auto.py' in path

    from muffin_peewee.migrate import Migrator

    migrator = Migrator(router.database, app=app)

    @migrator.create_table
    class Customer(peewee.Model):
        name = peewee.CharField()

    assert Customer == migrator.orm['customer']

    @migrator.create_table
    class Order(peewee.Model):
        number = peewee.CharField()

        customer = peewee.ForeignKeyField(Customer)

    assert Order == migrator.orm['order']
    migrator.run()

    migrator.add_columns(Order, finished=peewee.BooleanField(default=False))
    assert 'finished' in Order._meta.fields
    migrator.run()

    migrator.drop_columns('order', 'finished', 'customer')
    assert 'finished' not in Order._meta.fields
    migrator.run()

    migrator.add_columns(Order, customer=peewee.ForeignKeyField(Customer, null=True))
    assert 'customer' in Order._meta.fields
    migrator.run()

    migrator.rename_column(Order, 'number', 'identifier')
    assert 'identifier' in Order._meta.fields
    migrator.run()

    migrator.drop_not_null(Order, 'identifier')
    assert Order._meta.fields['identifier'].null
    assert Order._meta.columns['identifier'].null
    migrator.run()

    migrator.add_default(Order, 'identifier', 11)
    assert Order._meta.fields['identifier'].default == 11
    migrator.run()

    migrator.change_columns(Order, identifier=peewee.IntegerField(default=0))
    assert Order.identifier.db_field == 'int'
    migrator.run()

    Order.create(identifier=55)
    migrator.sql('UPDATE "order" SET identifier = 77;')
    migrator.run()
    order = Order.get()
    assert order.identifier == 77


def test_connect(app, model):
    from muffin_peewee.plugin import connect
    from muffin_peewee.mpeewee import schemes

    db = connect('postgres+pool://name:pass@localhost:5432/db')
    assert db
    assert isinstance(db, schemes['postgres+pool'])


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
