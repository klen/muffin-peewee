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
def model(app):

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

    migrator = Migrator(router.database)

    @migrator.create_table
    class Customer(peewee.Model):
        name = peewee.CharField()

    assert Customer == migrator.orm['customer']

    @migrator.create_table
    class Order(peewee.Model):
        number = peewee.CharField()

        customer = peewee.ForeignKeyField(Customer)

    assert Order == migrator.orm['order']

    migrator.add_columns(Order, finished=peewee.BooleanField(default=False))
    assert 'finished' in Order._meta.fields

    migrator.drop_columns('order', 'finished', 'customer')
    assert 'finished' not in Order._meta.fields

    migrator.add_columns(Order, customer=peewee.ForeignKeyField(Customer, null=True))
    assert 'customer' in Order._meta.fields
