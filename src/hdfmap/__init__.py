"""
hdfmap
Map objects within an HDF file and create a dataset namespace.

--- Usage ---
# HdfMap from NeXus file:
from hdfmap import create_nexus_map, load_hdf
hmap = create_nexus_map('file.nxs')
with load_hdf('file.nxs') as nxs:
    address = hmap.get_address('energy')
    energy = nxs[address][()]
    string = hmap.format_hdf(nxs, "the energy is {energy:.2f} keV")
    d = hmap.get_data_block(nxs)  # classic data table, d.scannable, d.metadata

# Shortcuts - single file reloading class
from hdfmap import NexusLoader
scan = NexusLoader('file.nxs')
[data1, data2] = scan.get_data(['dataset_name_1', 'dataset_name_2'])
data = scan.eval('dataset_name_1 * 100 + 2')
string = scan.format('my data is {dataset_name_1:.2f}')

# Shortcuts - multifile load data
from hdfmap import hdf_data, hdf_eval, hdf_format, hdf_image
all_data = hdf_data([f"file{n}.nxs" for n in range(100)], 'dataset_name')
normalised_data = hdf_eval(filenames, 'total / Transmission / (rc / 300.)')
descriptions = hdf_eval(filenames, 'Energy: {en:5.3f} keV')
image = hdf_image(filenames, index=31)


By Dr Dan Porter
Diamond Light Source Ltd
2024
"""

from .logging import set_logging_levels
from .hdfmap_class import HdfMap
from .nexus import NexusMap
from .file_functions import list_files, load_hdf, create_hdf_map, create_nexus_map
from .file_functions import hdf_data, hdf_image, hdf_eval, hdf_format, nexus_data_block
from .reloader_class import HdfLoader, NexusLoader


__all__ = [
    HdfMap, NexusMap, load_hdf, create_hdf_map, create_nexus_map,
    hdf_data, hdf_image, hdf_eval, hdf_format, nexus_data_block, HdfLoader, NexusLoader,
    set_logging_levels
]

__version__ = "0.5.0"
__date__ = "2024/08/02"


def version_info() -> str:
    return 'hdfmap version %s (%s)' % (__version__, __date__)


def module_info() -> str:
    import sys
    out = 'Python version %s' % sys.version
    out += '\n at: %s' % sys.executable
    out += '\n %s: %s' % (version_info(), __file__)
    # Modules
    import numpy
    out += '\n     numpy version: %s' % numpy.__version__
    import h5py
    out += '\n      h5py version: %s' % h5py.__version__
    # import imageio
    # out += '\n   imageio version: %s' % imageio.__version__
    try:
        import hdf5plugin
        out += '\n    hdf5plugin: %s' % hdf5plugin.version
    except ImportError:
        out += '\n    hdf5plugin: None'
    import os
    out += '\nRunning in directory: %s\n' % os.path.abspath('.')
    return out
