"""Support Peewee ORM in Muffin framework."""

# Package information
# ===================

__version__ = "1.0.6"
__project__ = "muffin-peewee"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"

from .plugin import Plugin                  # noqa
from .models import Model, TModel, Choices  # noqa
from .fields import JSONField               # noqa

try:
    from .debugtoolbar import DebugPanel # noqa
except ImportError:
    pass
