import importlib.metadata

# Dynamically get version.
__version__ = importlib.metadata.version(__name__)

# Remove import from our exported variables
del importlib

from .bit_field import *
from .dyn_value import *

from .types.type     import *
from .types.array    import *
from .types.numeric  import *
from .types.string   import *
from .types.enum     import *
from .types.default  import *
from .types.optional import *
from .types.misc     import *

from .packets import *

from . import io
from . import util
from . import test
