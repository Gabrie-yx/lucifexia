"""
lucifexbootstrap module compatibility wrapper.
Redirects all imports seamlessly to lucifex_bootstrap.
"""
import sys
import lucifex_bootstrap

sys.modules["lucifexbootstrap"] = lucifex_bootstrap
from lucifex_bootstrap import *
