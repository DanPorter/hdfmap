"""
Nexus Related functions and nexus class
"""

import h5py

from .hdfmap_class import HdfMap, SEP


NX_LOCALNAME = 'local_name'
NX_DEFAULT = 'default'
NX_MEASUREMENT = 'measurement'
NX_SCAN_SHAPE_ADDRESS = 'entry1/scan_shape'
NX_SIGNAL = 'signal'
NX_AXES = 'axes'
NX_DETECTOR = 'NXdetector'
NX_DETECTOR_DATA = 'data'


def get_nexus_axes_datasets(hdf_object: h5py.File) -> tuple[list[h5py.Dataset], h5py.Dataset]:
    """
    Nexus compliant method of finding default plotting axes in hdf files
     - find "default" entry group in top File group
     - find "default" data group in entry
     - find "axes" attr in default data
     - find "signal" attr in default data
     - generate addresses of signal and axes
     if not nexus compliant, raises KeyError
    This method is very fast but only works on nexus compliant files
    :param hdf_object: open HDF file object, i.e. h5py.File(...)
    :return axes_datasets: list of dataset objects for axes
    :return signal_dataset: dataset object for plot axis
    """
    # From: https://manual.nexusformat.org/examples/python/plotting/index.html
    # find the default NXentry group
    nx_entry = hdf_object[
        hdf_object.attrs["default"] if "default" in hdf_object.attrs else next(iter(hdf_object.keys()))
    ]
    # find the default NXdata group
    nx_data = nx_entry[nx_entry.attrs["default"] if "default" in nx_entry.attrs else "measurement"]
    # find the axes field(s)
    if isinstance(nx_data.attrs["axes"], (str, bytes)):
        axes_datasets = [nx_data[nx_data.attrs["axes"]]]
    else:
        axes_datasets = [nx_data[_axes] for _axes in nx_data.attrs["axes"]]
    # find the signal field
    signal_dataset = nx_data[nx_data.attrs["signal"]]
    return axes_datasets, signal_dataset


def get_strict_nexus_axes_datasets(hdf_object: h5py.File) -> tuple[list[h5py.Dataset], h5py.Dataset]:
    """
    Nexus compliant method of finding default plotting axes in hdf files
     - find "default" entry group in top File group
     - find "default" data group in entry
     - find "axes" attr in default data
     - find "signal" attr in default data
     - generate addresses of signal and axes
     if not nexus compliant, raises KeyError
    This method is very fast but only works on nexus compliant files
    :param hdf_object: open HDF file object, i.e. h5py.File(...)
    :return axes_datasets: list of dataset objects for axes
    :return signal_dataset: dataset object for plot axis
    """
    # From: https://manual.nexusformat.org/examples/python/plotting/index.html
    # find the default NXentry group
    nx_entry = hdf_object[hdf_object.attrs["default"]]
    # find the default NXdata group
    nx_data = nx_entry[nx_entry.attrs["default"]]
    # find the axes field(s)
    if isinstance(nx_data.attrs["axes"], (str, bytes)):
        axes_datasets = [nx_data[nx_data.attrs["axes"]]]
    else:
        axes_datasets = [nx_data[_axes] for _axes in nx_data.attrs["axes"]]
    # find the signal field
    signal_dataset = nx_data[nx_data.attrs["signal"]]
    return axes_datasets, signal_dataset


class NexusMap(HdfMap):
    """
    HdfMap for Nexus (.nxs) files
    """

    def _load_defaults(self, hdf_file):
        """Load Nexus default axes and signal"""
        super()._load_defaults(hdf_file)
        try:
            axes_datasets, signal_dataset = get_nexus_axes_datasets(hdf_file)
            if axes_datasets[0].name in hdf_file:
                self.arrays[NX_AXES] = axes_datasets[0].name
                if self._debug:
                    self._debug_logger(f"DEFAULT axes: {axes_datasets[0].name}")
            if signal_dataset.name in hdf_file:
                self.arrays[NX_SIGNAL] = signal_dataset.name
                if self._debug:
                    self._debug_logger(f"DEFAULT signal: {signal_dataset.name}")
        except KeyError:
            pass

    def populate(self, hdf_file: h5py.File, groups=None):
        """
        Populate only datasets from first entry, with scannables from given groups
        :param hdf_file: HDF File object
        :param groups: list of group names or NXClass names to search for datasets
        :return:
        """
        self.filename = hdf_file.filename

        # Add defaults to arrays
        self._load_defaults(hdf_file)

        # find default or first entry
        nx_entry = hdf_file[
            hdf_file.attrs[NX_DEFAULT] if NX_DEFAULT in hdf_file.attrs else next(iter(hdf_file.keys()))
        ]
        if self._debug:
            self._debug_logger(f"NX Entry: {nx_entry.name}")
        self._populate(nx_entry, top_address=nx_entry.name, groups=groups)

        # find the default NXdata group and generate the scannables list
        nx_data = nx_entry.get(nx_entry.attrs[NX_DEFAULT] if NX_DEFAULT in nx_entry.attrs else NX_MEASUREMENT)
        if nx_data:
            if self._debug:
                self._debug_logger(f"NX Data: {nx_data.name}")
            self.generate_scannables_from_group(nx_data)

        # find the NXdetector group and assign the image data
        if NX_DETECTOR in self.classes:
            address = self.classes[NX_DETECTOR][0] + SEP + NX_DETECTOR_DATA
            if self._debug:
                self._debug_logger(f"NX Detector: {address} : {hdf_file.get(address)}")
            if address in hdf_file:
                self.image_data[NX_DETECTOR] = address

    def get_image_address(self) -> str | None:
        """Return address of first dataset named 'data'"""
        if NX_DETECTOR in self.image_data:
            return self.image_data[NX_DETECTOR]

