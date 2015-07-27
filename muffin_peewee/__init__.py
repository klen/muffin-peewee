"""
    muffin-peewee description.

"""

# Package information
# ===================

__version__ = "0.0.41"
__project__ = "muffin-peewee"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"

from .plugin import Plugin          # noqa
from .models import Model           # noqa

try:
    from .debugtoolbar import DebugPanel # noqa
except ImportError:
    pass
