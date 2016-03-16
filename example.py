import muffin
import datetime
import peewee


# Setup application
app = muffin.Application(
    'example',

    PLUGINS=(
        'muffin_peewee',
    ),
    PEEWEE_CONNECTION='sqlite:///example.db',
)
