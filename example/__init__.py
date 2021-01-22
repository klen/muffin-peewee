import muffin
import muffin_peewee


# Setup application
app = muffin.Application(
    'example',

    DEBUG=True,
    PEEWEE_CONNECTION='sqlite+async:///example.db',
    PEEWEE_MIGRATIONS_PATH='example/migrations',
)
db = muffin_peewee.Plugin(app)

# Register views
from example.views import *  # noqa
