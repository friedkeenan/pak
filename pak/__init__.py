try:
    import importlib.metadata as importlib_metadata
except ImportError:
    # TODO: Remove this when Python 3.7 support is dropped.
    import importlib_metadata

# Dynamically get version.
__version__ = importlib_metadata.version(__name__)

# Remove import from our exported variables
del importlib_metadata

from .dyn_value import *

from .types.type     import *
from .types.array    import *
from .types.numeric  import *
from .types.string   import *
from .types.bit_mask import *
from .types.compound import *
from .types.enum     import *
from .types.default  import *
from .types.optional import *
from .types.misc     import *

from .packets import *

from . import io
from . import util
from . import test
