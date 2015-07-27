import muffin


# Setup application
app = muffin.Application(
    'example',

    PLUGINS=(
        'muffin_peewee',
    ),
    PEEWEE_CONNECTION='sqlite:///example.db',
    PEEWEE_MIGRATIONS_PATH='example/migrations',
)

# Register views
from example.views import *  # noqa
