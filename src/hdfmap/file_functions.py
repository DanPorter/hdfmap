import os
import h5py
import numpy as np

from .hdfmap_class import HdfMap
from .nexus import NexusMap


EXTENSIONS = ['.nxs', '.hdf', '.hdf5', '.h5']
DEFAULT_EXTENSION = EXTENSIONS[0]
DEFAULT_ADDRESS = "entry1/scan_command"


def load_hdf(hdf_filename: str) -> h5py.File:
    """Load hdf file, return h5py.File object"""
    return h5py.File(hdf_filename, 'r')


def list_files(folder_directory: str, extension=DEFAULT_EXTENSION) -> list[str]:
    """Return list of files in directory with extension, returning list of full file paths"""
    try:
        return sorted(
            (file.path for file in os.scandir(folder_directory) if file.is_file() and file.name.endswith(extension)),
            key=lambda x: os.path.getmtime(x)
        )
    except FileNotFoundError:
        return []


def create_hdf_map(hdf_filename: str, debug: bool = False) -> HdfMap:
    """
    Create a HdfMap from a hdf file
    :param hdf_filename: str filename of hdf file
    :param debug: if True, displays debugging info
    :return: HdfMap
    """
    hdf_map = HdfMap()
    hdf_map.debug(debug)
    with load_hdf(hdf_filename) as hdf:
        hdf_map.populate(hdf)
    size = hdf_map.most_common_size()
    hdf_map.generate_scannables(size)
    return hdf_map


def create_nexus_map(hdf_filename: str, groups: None | list[str] = None,
                     default_entry_only: bool = False, debug: bool = False) -> NexusMap:
    """
    Create a HdfMap from a NeXus file, loading default parameters and allowing a reduced, single entry map
    :param hdf_filename: str filename of hdf file
    :param groups: list of groups to collect datasets from
    :param default_entry_only: if True, only the first or default entry will be loaded
    :param debug: if True, displays debugging info
    :return: NexusMap
    """
    hdf_map = NexusMap()
    hdf_map.debug(debug)
    with load_hdf(hdf_filename) as hdf:
        hdf_map.populate(hdf, groups=groups, default_entry_only=default_entry_only)
    if not hdf_map.scannables:
        print('NXdata not found, getting scannables from most common array size')
        size = hdf_map.most_common_size()
        hdf_map.generate_scannables(size)
    return hdf_map


def hdf_data(filenames: str | list[str], name_or_address: str | list[str], hdf_map: HdfMap = None,
             index=(), default=None, debug=False, fixed_output=False):
    """
    General purpose function to retrieve data from HDF files
    :param filenames: str or list of str - file paths
    :param name_or_address: str or list of str - names or addresses of HDF datasets
    :param hdf_map: HdfMap object, or None to generate from first file
    :param index: dataset index or slice
    :param default: value to give if dataset doesn't exist in file
    :param debug: prints output if True
    :param fixed_output: if True, always returns list of list
    :return if single file, single dataset: single value
    :return if multi file or multi dataset: list, len(filenames) or len(name_or_address)
    :return if multi file and multi dataset: list[files: list[names]]
    """
    # cast as 1D arrays
    filenames = np.reshape(filenames, -1)
    name_or_address = np.reshape(name_or_address, -1)
    # generate hdf_map
    if hdf_map is None:
        hdf_map = create_hdf_map(filenames[0], debug=debug)
    out = []
    for filename in filenames:
        if debug:
            print(f"\nHDF file: {filename}")
        with load_hdf(filename) as hdf:
            out.append([hdf_map.get_data(hdf, name, index=index, default=default) for name in name_or_address])
    if fixed_output:
        return out
    if filenames.size == 1 and name_or_address.size == 1:
        return out[0][0]
    if filenames.size == 1 and name_or_address.size > 1:
        return out[0]
    if name_or_address.size == 1:
        return [val[0] for val in out]
    return out


def hdf_eval(filenames: str | list[str], expression: str, hdf_map: HdfMap = None, debug=False, fixed_output=False):
    """
    Evaluate expression using dataset names
    :param filenames: str or list of str - file paths
    :param expression: str expression to evaluate in each file, e.g. "roi2_sum / Transmission"
    :param hdf_map: HdfMap object, or None to generate from first file
    :param debug: prints output if True
    :param fixed_output: if True, always returns list len(filenames)
    :return if single file: single output
    :return if multi file: list, len(filenames)
    """
    # cast as 1D arrays
    filenames = np.reshape(filenames, -1)
    # generate hdf_map
    if hdf_map is None:
        hdf_map = create_hdf_map(filenames[0], debug=debug)
    out = []
    for filename in filenames:
        if debug:
            print(f"\nHDF file: {filename}")
        with load_hdf(filename) as hdf:
            out.append(hdf_map.eval(hdf, expression))
    if not fixed_output and filenames.size == 1:
        return out[0]
    return out


def hdf_format(filenames: str | list[str], expression: str, hdf_map: HdfMap = None, debug=False, fixed_output=False):
    """
    Evaluate string format expression using dataset names
    :param filenames: str or list of str - file paths
    :param expression: str expression to evaluate in each file, e.g. "the energy is {en:.2f} keV"
    :param hdf_map: HdfMap object, or None to generate from first file
    :param debug: prints output if True
    :param fixed_output: if True, always returns list len(filenames)
    :return if single file: single output
    :return if multi file: list, len(filenames)
    """
    # cast as 1D arrays
    filenames = np.reshape(filenames, -1)
    # generate hdf_map
    if hdf_map is None:
        hdf_map = create_hdf_map(filenames[0], debug=debug)
    out = []
    for filename in filenames:
        if debug:
            print(f"\nHDF file: {filename}")
        with load_hdf(filename) as hdf:
            out.append(hdf_map.format_hdf(hdf, expression))
    if not fixed_output and filenames.size == 1:
        return out[0]
    return out


def hdf_image(filenames: str | list[str], index: slice = None, hdf_map: HdfMap = None, debug=False, fixed_output=False):
    """
    Evaluate string format expression using dataset names
    :param filenames: str or list of str - file paths
    :param index: index or slice of dataset volume, or None to use middle index
    :param hdf_map: HdfMap object, or None to generate from first file
    :param debug: prints output if True
    :param fixed_output: if True, always returns list len(filenames)
    :return if single file: single output - numpy array
    :return if multi file: list, len(filenames)
    """
    # cast as 1D arrays
    filenames = np.reshape(filenames, -1)
    # generate hdf_map
    if hdf_map is None:
        hdf_map = create_hdf_map(filenames[0], debug=debug)
    out = []
    for filename in filenames:
        if debug:
            print(f"\nHDF file: {filename}")
        with load_hdf(filename) as hdf:
            out.append(hdf_map.get_image(hdf, index=index))
    if not fixed_output and filenames.size == 1:
        return out[0]
    return out


def nexus_data_block(filenames: str | list[str], hdf_map: HdfMap = None, debug=False, fixed_output=False):
    """
    Create classic dict like dataloader objects from nexus files
    E.G.
        d = nexus_data_block('filename')
        d.scannable -> array
        d.metadata.filename -> value
        d.keys() -> list of items

    :param filenames: str or list of str - file paths
    :param hdf_map: HdfMap object, or None to generate from first file
    :param debug: prints output if True
    :param fixed_output: if True, always returns list len(filenames)
    :return if single file: single output - dict like DataObject
    :return if multi file: list, len(filenames)
    """
    # cast as 1D arrays
    filenames = np.reshape(filenames, -1)
    # generate hdf_map
    if hdf_map is None:
        hdf_map = create_nexus_map(filenames[0], debug=debug)
    out = []
    for filename in filenames:
        if debug:
            print(f"\nHDF file: {filename}")
        with load_hdf(filename) as hdf:
            out.append(hdf_map.get_data_block(hdf))
    if not fixed_output and filenames.size == 1:
        return out[0]
    return out

