"""
Profiles module for SWE-smith.

This module contains repository profiles for different programming languages
and provides a global registry for accessing all profiles.
"""

from .base import RepoProfile, registry

# Auto-import all profile modules to populate the registry
from . import c
from . import cpp
from . import csharp
from . import java
from . import javascript
from . import php
from . import typescript
from . import python
from . import golang
from . import rust
# this import is needed so r concrete profiles self-register on module load.
from . import r

__all__ = ["RepoProfile", "registry"]
