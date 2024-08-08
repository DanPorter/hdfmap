"""
Nexus Related functions and nexus class
"""

import h5py

from .logging import create_logger
from .hdfmap_class import HdfMap, build_hdf_path, generate_identifier

NX_CLASS = 'NX_class'
NX_ENTRY = b'NXentry'
NX_DATA = b'NXdata'
NX_LOCALNAME = 'local_name'
NX_DEFAULT = 'default'
NX_MEASUREMENT = 'measurement'
NX_SCANFIELDS = 'scan_fields'
NX_SIGNAL = 'signal'
NX_AXES = 'axes'
NX_DETECTOR = 'NXdetector'
NX_DETECTOR_DATA = 'data'
logger = create_logger(__name__)


def check_nexus_class(hdf_group: h5py.Group, nxclass: bytes) -> bool:
    """
    Check if hdf_group is a certain NX_class
    :param hdf_group:
    :param nxclass:
    :return:
    """
    return True if hdf_group and NX_CLASS in hdf_group.attrs and hdf_group.attrs[NX_CLASS] == nxclass else False


def default_nxentry(hdf_file: h5py.File) -> str | bytes:
    """Return the default NXentry path, or the first NXentry if there is no default, errors if no NXentry"""
    return entry if (
            NX_DEFAULT in hdf_file.attrs and
            isinstance(hdf_file.get(entry := hdf_file.attrs[NX_DEFAULT]), h5py.Group)
    ) else next(path for path in hdf_file if check_nexus_class(hdf_file.get(path), NX_ENTRY))


def default_nxdata(entry_group: h5py.Group) -> str | bytes:
    """Return the default NXdata path within an NXentry group"""
    nx_data_name = entry_group.attrs[NX_DEFAULT] if NX_DEFAULT in entry_group.attrs else NX_MEASUREMENT
    if nx_data_name not in entry_group:
        nx_data_name = next(name for name in entry_group if check_nexus_class(entry_group.get(name), NX_DATA))
    return nx_data_name


def find_nexus_data(hdf_file: h5py.File) -> tuple[list[str], str]:
    """
    Nexus compliant method of finding default plotting axes in hdf files
     - find "default" entry group in top File group
     - find "default" data group in entry (or 'measurement', or first 'NXdata')
     - find "axes" attr in default data
     - find "signal" attr in default data
     - generate paths of signal and axes
     if not nexus compliant, raises KeyError
    This method is very fast but only works on nexus compliant files
    :param hdf_file: open HDF file object, i.e. h5py.File(...)
    :return axes_paths: list of str hdf paths for axes datasets
    :return signal_path: str hdf path for signal dataset
    """
    # From: https://manual.nexusformat.org/examples/python/plotting/index.html
    # find the default NXentry group
    nx_entry_name = default_nxentry(hdf_file)
    nx_entry = hdf_file[nx_entry_name]
    # find the default NXdata group
    nx_data_name = default_nxdata(nx_entry)
    nx_data = nx_entry[nx_data_name]
    # find the axes field(s)
    if isinstance(axes := nx_data.attrs[NX_AXES], (str, bytes)):
        axes_paths = [build_hdf_path(nx_entry_name, nx_data_name, axes)]
    else:
        axes_paths = [build_hdf_path(nx_entry_name, nx_data_name, _axes) for _axes in axes]
    # get the signal field
    signal_path = build_hdf_path(nx_entry_name, nx_data_name, nx_data.attrs[NX_SIGNAL])
    return axes_paths, signal_path


def find_nexus_data_strict(hdf_file: h5py.File) -> tuple[list[h5py.Dataset], h5py.Dataset]:
    """
    Nexus compliant method of finding default plotting axes in hdf files
     - find "default" entry group in top File group
     - find "default" data group in entry
     - find "axes" attr in default data
     - find "signal" attr in default data
     - generate paths of signal and axes
     if not nexus compliant, raises KeyError
    This method is very fast but only works on nexus compliant files
    :param hdf_file: open HDF file object, i.e. h5py.File(...)
    :return axes_datasets: list of dataset objects for axes
    :return signal_dataset: dataset object for plot axis
    """
    # From: https://manual.nexusformat.org/examples/python/plotting/index.html
    # find the default NXentry group
    nx_entry = hdf_file[hdf_file.attrs["default"]]
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

    Extends the HdfMap class with additional behaviours for NeXus files.
    http://www.nexusformat.org/

    E.G.
    nxmap = NexusMap()
    with h5py.File('file.nxs', 'r') as nxs:
        nxmap.populate(nxs, default_entry_only=True)  # populates only from the default entry

    # Special behaviour
    nxmap['axes'] -> return path of default axes dataset
    nxmap['signal'] -> return path of default signal dataset
    """

    def __repr__(self):
        return f"NexusMap based on '{self.filename}'"

    def _default_nexus_paths(self, hdf_file):
        """Load Nexus default axes and signal"""
        try:
            axes_paths, signal_path = find_nexus_data(hdf_file)
            if axes_paths and axes_paths[0] in hdf_file:
                self.arrays[NX_AXES] = axes_paths[0]
                logger.info(f"DEFAULT axes: {axes_paths}")
            if signal_path in hdf_file:
                self.arrays[NX_SIGNAL] = signal_path
                logger.info(f"DEFAULT signal: {signal_path}")
        except KeyError:
            pass

    def _scannables_from_scan_fields_or_nxdata(self, hdf_file: h5py.File):
        """Generate scannables from scan_field names or default NXdata"""
        # find 'scan_fields' to generate scannables list
        if NX_SCANFIELDS in self.arrays:
            scan_fields_path = self.arrays[NX_SCANFIELDS]
            scan_fields = hdf_file[scan_fields_path][()]
            logger.info(f"NX ScanFields: {scan_fields_path}: {scan_fields}")
            self.generate_scannables_from_names(scan_fields)
        else:
            # find the default NXdata group and generate the scannables list
            nx_entry = hdf_file.get(default_nxentry(hdf_file))
            nx_data = nx_entry.get(default_nxdata(nx_entry))
            logger.info(f"{nx_entry}, {nx_data}")
            if nx_data:
                logger.info(f"NX Data: {nx_data.name}")
                self.generate_scannables_from_group(nx_data)

        if not self.scannables:
            logger.warning("No NXdata found, scannables not populated!")

    def _image_data_from_nxdetector(self):
        """find the NXdetector group and assign the image data"""
        self.image_data = {}
        if NX_DETECTOR in self.classes:
            for group_path in self.classes[NX_DETECTOR]:
                detector_name = generate_identifier(group_path)
                data_path = build_hdf_path(group_path, NX_DETECTOR_DATA)
                if data_path in self.datasets and len(self.datasets[data_path].shape) > 1:
                    self.image_data[detector_name] = data_path

        if not self.image_data:
            logger.warning("!!!Warning: No NXdetector found, image_data not populated!")

    def populate(self, hdf_file: h5py.File, groups=None, default_entry_only=False):
        """
        Populate only datasets from default or first entry, with scannables from given groups.
        Automatically load defaults (axes, signal) and generate scannables from default group
        :param hdf_file: HDF File object
        :param groups: list of group names or NXClass names to search for datasets, within default entry
        :param default_entry_only: if True, only the first or default entry will be loaded
        """
        self.filename = hdf_file.filename

        # Add defaults to arrays
        self._default_nexus_paths(hdf_file)

        if default_entry_only:
            entries = [default_nxentry(hdf_file)]
        else:
            entries = [entry for entry in hdf_file if check_nexus_class(hdf_file.get(entry), NX_ENTRY)]

        for entry in entries:
            # find default or first entry
            nx_entry = hdf_file.get(entry)
            if nx_entry is None:
                logger.warning(
                    f"NX Entry {entry} doesn't exist - may be a missing link.\n" +
                    f"Missing link: {hdf_file.get(entry, getlink=True)}"
                )
                continue  # group may be missing due to a broken link
            hdf_path = build_hdf_path(entry)
            logger.debug(f"NX Entry: {hdf_path}")
            self._store_group(nx_entry, hdf_path, entry)
            self._populate(nx_entry, root=hdf_path, groups=groups)  # nx_entry.name can be wrong!

        if not self.datasets:
            logger.warning("!!!Warning: No datasets found!")

        self._scannables_from_scan_fields_or_nxdata(hdf_file)

        # find the NXdetector group and assign the image data
        self._image_data_from_nxdetector()
