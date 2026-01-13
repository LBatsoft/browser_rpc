"""
Browser RPC Core Package
"""

from .config import BrowserRPCConfig, get_config
from .cdp_client import BrowserPool

__all__ = ['BrowserRPCConfig', 'get_config', 'BrowserPool']

