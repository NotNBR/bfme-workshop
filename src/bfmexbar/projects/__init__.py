"""Import authored project code directly from maps/ and showcases/.

For example bfmexbar.projects.maps.eight_kingdoms.build is backed by
maps/eight-kingdoms/build.py. This keeps one copy of each project's source.
"""
import importlib.machinery
import re
import sys
import types
from bfmexbar.paths import ROOT


def namespace(name, directory):
    module = types.ModuleType(name)
    module.__path__ = [str(directory)]
    module.__package__ = name
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    module.__spec__.submodule_search_locations = module.__path__
    sys.modules[name] = module
    return module


for kind in ('maps', 'showcases'):
    parent = namespace(__name__ + '.' + kind, ROOT / 'projects' / kind)
    globals()[kind] = parent
    for directory in sorted((ROOT / 'projects' / kind).glob('*')):
        if directory.is_dir() and re.fullmatch(r'[a-z][a-z0-9-]*', directory.name):
            key = directory.name.replace('-', '_')
            setattr(parent, key, namespace(parent.__name__ + '.' + key, directory))
