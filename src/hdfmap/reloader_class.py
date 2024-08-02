"""
Reloader class
"""

import h5py
import numpy as np

from .hdfmap_class import HdfMap
from .nexus import NexusMap
from .file_functions import load_hdf, create_hdf_map, create_nexus_map


class HdfLoader:
    """
    HDF Loader
    contains the filename and hdfmap for a HDF file, the hdfmap contains all the dataset paths and a
    namespace, allowing data to be called from the file using variable names, loading only the required datasets
    for each operation.
    E.G.
        hdf = HdfLoader('file.hdf')
        [data1, data2] = hdf.get_data(['dataset_name_1', 'dataset_name_2'])
        data = hdf.eval('dataset_name_1 * 100 + 2')
        string = hdf.format('my data is {dataset_name_1:.2f}')
    """

    def __init__(self, hdf_filename: str, hdf_map: HdfMap | None = None):
        self.filename = hdf_filename
        if hdf_map is None:
            self.map = create_hdf_map(hdf_filename)
        else:
            self.map = hdf_map

    def __repr__(self):
        return f"HdfReloader('{self.filename}')"

    def __str__(self):
        with self._load() as hdf:
            out = self.map.info_data(hdf)
        return out

    def __getitem__(self, item):
        return self.get_data(item)

    def __call__(self, expression):
        return self.eval(expression)

    def _load(self) -> h5py.File:
        return load_hdf(self.filename)

    def get_hdf_path(self, name_or_path: str) -> str or None:
        return self.map.get_path(name_or_path)

    def find_hdf_paths(self, name: str) -> list[str]:
        return self.map.find_paths(name)

    def find_names(self, name: str) -> list[str]:
        return self.map.find_names(name)

    def get_data(self, *name_or_path, index: slice = (), direct_load=False):
        name_or_path = np.reshape(name_or_path, -1)
        with self._load() as hdf:
            out = [self.map.get_data(hdf, name, index, direct_load) for name in name_or_path]
        if name_or_path.size == 1:
            return out[0]
        return out

    def get_image(self, index: slice = None) -> np.ndarray:
        """
        Get image data from file, using default image path
        :param hdf_file: hdf file object
        :param index: (slice,) or None to take the middle image
        :return: numpy array of image
        """
        with self._load() as hdf:
            return self.map.get_image(hdf, index)

    def get_metadata(self, defaults=None):
        with self._load() as hdf:
            return self.map.get_metadata(hdf, default=defaults)

    def get_scannables(self):
        with self._load() as hdf:
            return self.map.get_scannables(hdf)

    def eval(self, expression: str):
        with self._load() as hdf:
            return self.map.eval(hdf, expression)

    def format(self, expression: str):
        with self._load() as hdf:
            return self.map.format_hdf(hdf, expression)


class NexusLoader(HdfLoader):
    """
    Nexus Loader
    contains the filename and hdfmap for a NeXus file, the hdfmap contains all the dataset paths and a
    namespace, allowing data to be called from the file using variable names, loading only the required datasets
    for each operation.
    E.G.
        hdf = NexusLoader('file.hdf')
        [data1, data2] = hdf.get_data(['dataset_name_1', 'dataset_name_2'])
        data = hdf.eval('dataset_name_1 * 100 + 2')
        string = hdf.format('my data is {dataset_name_1:.2f}')
    """

    def __init__(self, nxs_filename: str, hdf_map: NexusMap | None = None):
        if not hdf_map:
            hdf_map = create_nexus_map(nxs_filename)
        super().__init__(nxs_filename, hdf_map)
