"""
hdfmap class definition
"""
import typing
from collections import defaultdict

import numpy as np
import h5py

from .logging import create_logger
from .eval_functions import expression_safe_name, extra_hdf_data, eval_hdf, format_hdf, dataset2data

try:
    import hdf5plugin  # required for compressed data
except ImportError:
    print('Warning: hdf5plugin not available.')

# parameters
SEP = '/'  # HDF path separator
LOCAL_NAME = 'local_name'  # dataset attribute name for alt_name
VALUE = 'value'  # omit this name in paths when determining identifier
# logger
logger = create_logger(__name__)


class Group(typing.NamedTuple):
    nx_class: str
    name: str
    attrs: dict
    datasets: list[str]


class Dataset(typing.NamedTuple):
    name: str
    size: int
    shape: tuple[int]
    attrs: dict


def generate_identifier(hdf_path: str | bytes) -> str:
    """
    Generate a valid python identifier from a hdf dataset path or other string
     - Decodes to ascii
     - omits '/value'
     - splits by path separator (/) and takes final element
     - converts special characters to '_'
     - removes replication of strings separated by '_'
    E.G.
        /entry/group/motor1 >> "motor1"
        /entry/group/motor/value >> "motor"
        /entry/group/subgroup.motor >> "subgroup_motor"
        motor.motor >> "motor"
    :param hdf_path: str hdf path address
    :return: str expression safe name
    """
    if hasattr(hdf_path, 'decode'):  # Byte string
        hdf_path = hdf_path.decode('ascii')
    omit = f"/{VALUE}"
    if hdf_path.endswith(omit):
        hdf_path = hdf_path[:-len(omit)]  # omit 'value'
    substrings = hdf_path.split(SEP)
    name = expression_safe_name(substrings[-1])
    # remove replication (handles local_names 'name.name' convention)
    return '_'.join(dict.fromkeys(name.split('_')))


def build_hdf_path(*args: str | bytes) -> str:
    """
    Build path from string or bytes arguments
        '/entry/measurement' = build_hdf_path(b'entry', 'measurement')
    :param args: str or bytes arguments
    :return: str hdf path
    """
    return SEP + SEP.join((arg.decode() if isinstance(arg, bytes) else arg).strip(SEP) for arg in args)


def disp_dict(mydict: dict, indent: int = 10) -> str:
    return '\n'.join([f"{key:>{indent}}: {value}" for key, value in mydict.items()])


class DataHolder(dict):
    """
    Convert dict to class that looks like a class object with key names as attributes
    Replicates slightly the old scisoftpy.dictutils.DataHolder class, also known as DLS dat format.
        obj = DataHolder({'item1': 'value1'}, 'docs')
        obj['item1'] -> 'value1'
        obj.item1 -> 'value1'
        help(obj) -> 'docs'
    """

    def __init__(self, ini_dict: dict, docstr: str = None):
        # copy dict
        super().__init__(**ini_dict)
        # assign attributes
        for name, value in ini_dict.items():
            setattr(self, name, value)
        # update doc string
        if docstr:
            self.__doc__ = docstr

    def __repr__(self):
        return "DataHolder({})"

    def __str__(self):
        return f"DataHolder({{\n{disp_dict(self)}\n}})"


class HdfMap:
    """
    HdfMap object, container for paths of different objects in an HDF file

        with h5py.File('file.hdf') as hdf:
            map = HdfMap(hdf)

        map.get_path('data') -> '/entry/measurement/data'
        map['data'] -> '/entry/measurement/data'

        with h5py.File('another_file.hdf') as hdf:
            data = map.get_data(hdf, 'data')
            array = map.get_scannables_array(hdf)
            metadata = map.get_metadata(hdf)
            out = map.eval(hdf, 'data / 10')
            outstr = map.format(hdf, 'the data looks like: {data}')

    Objects within the HDF file are separated into Groups and Datasets. Each object has a
    defined 'path' and 'name' paramater, as well as other attributes
        path -> '/entry/measurement/data' -> the location of an object within the file
        name -> 'data' -> an path expressed as a simple variable name
    Paths are unique location within the file but can be used to identify similar objects in other files
    Names may not be unique within a file and are generated from the final element of the hdf path.
     - When multiple paths produce the same name, the name is overwritten each time, so the last path in the
    file has priority.
     - Names are also stored using the 'local_name' attribute, if it exists

    Names of different types of datasets are stored for arrays (size > 0) and values (size 0)
    Names for scannables relate to all arrays of a particular size
    A combined list of names is provided where scannables > arrays > values



    Attributes:
        map.groups      stores attributes of each group by path
        map.classes     stores list of group paths by nx_class
        map.datasets    stores attributes of each dataset by path
        map.arrays      stores array dataset paths by name
        map.values      stores value dataset paths by name
        map.scannables  stores array dataset paths with given size, by name
        map.combined    stores array and value paths (arrays overwrite values)
        map.image_data  stores dataset paths of image data
    E.G.
        map.groups = {'/hdf/group': ('class', 'name', {attrs}, [datasets])}
        map.classes = {'class_name': ['/hdf/group1', '/hdf/group2']}
        map.datasets = {'/hdf/group/dataset': ('name', size, shape, {attrs})}
        map.arrays = {'name': '/hdf/group/dataset'}
        map.values = {'name': '/hdf/group/dataset'}
        map.scannables = {'name': '/hdf/group/dataset'}
        map.image_data = {'name': '/hdf/group/dataset'}

    Methods:
        map.populate(h5py.File) -> populates the dictionaries using the  given file
        map.generate_scannables(array_size) -> populates scannables namespace with arrays of same size
        map.most_common_size -> returns the most common dataset size > 1
        map.get_size('name_or_path') -> return dataset size
        map.get_shape('name_or_path') -> return dataset size
        map.get_attr('name_or_path', 'attr') -> return value of dataset attribute
        map.get_path('name_or_group_or_class') -> returns path of object with name
        map.get_image_path() -> returns default path of detector dataset (or largest dataset)
        map.get_group_path('name_or_path_or_class') -> return path of group with class
        map.get_group_datasets('name_or_path_or_class') -> return list of dataset pathes in class
    File Methods:
        map.get_metadata(h5py.File) -> returns dict of value datasets
        map.get_scannables(h5py.File) -> returns dict of scannable datasets
        map.get_scannalbes_array(h5py.File) -> returns numpy array of scannable datasets
        map.get_data_block(h5py.File) -> returns dict like object with metadata and scannables
        map.get_image(h5py.File, index) -> returns image data
        map.get_data(h5py.File, 'name') -> returns data from dataset
        map.eval(h5py.File, 'expression') -> returns output of expression
        map.format(h5py.File, 'string {name}') -> returns output of str expression
    """

    def __init__(self, file: h5py.File | None = None):
        self.filename = ''
        self.groups = {}  # stores attributes of each group by path
        self.datasets = {}  # stores attributes of each dataset by path
        self.classes = defaultdict(lambda: [])  # stores lists of group paths by nx_class
        self.arrays = {}  # stores array dataset paths by name
        self.values = {}  # stores value dataset paths by name
        self.scannables = {}  # stores array dataset paths with given size, by name
        self.combined = {}  # stores array and value paths (arrays overwrite values)
        self.image_data = {}  # stores dataset paths of image data
        self._default_image_path = None

        if isinstance(file, h5py.File):
            self.populate(file)

    def __getitem__(self, item):
        return self.combined[item]

    def __iter__(self):
        return iter(self.combined)

    def __contains__(self, item):
        return item in self.combined or item in self.datasets

    def __repr__(self):
        return f"HdfMap based on '{self.filename}'"

    def __str__(self):
        return f"{repr(self)}\n{self.info_names()}\n{self.info_scannables()}"

    def info_groups(self):
        """Return str info on groups"""
        out = f"{repr(self)}\n"
        out += "Groups:\n"
        out += disp_dict(self.groups, 10)
        out += '\n\nClasses:\n'
        out += disp_dict(self.classes, 10)
        return out

    def info_datasets(self):
        """Return str info on datasets"""
        out = f"{repr(self)}\n"
        out += "Datasets:\n"
        out += disp_dict(self.datasets, 10)
        return out

    def info_dataset_types(self):
        """Return str info on dataset types"""
        out = "Values:\n"
        out += disp_dict(self.values, 10)
        out += "Arrays:\n"
        out += '\n'.join([
            f"{name:>30}: {str(self.datasets[path].shape):10} : {path:60}"
            for name, path in self.arrays.items()
        ])
        out += "Images:\n"
        out += '\n'.join([
            f"{name:>30}: {str(self.datasets[path].shape):10} : {path:60}"
            for name, path in self.image_data.items()
        ])
        return out

    def info_names(self):
        """Return str info on combined namespace"""
        out = "Combined Namespace:\n"
        out += '\n'.join([
            f"{name:>30}: {str(self.datasets[path].shape):10} : {path:60}"
            for name, path in self.combined.items()
        ])
        return out

    def info_scannables(self):
        """Return str info on scannables namespace"""
        out = "Scannables Namespace:\n"
        out += '\n'.join([
            f"{name:>30}: {str(self.datasets[path].shape):10} : {path:60}"
            for name, path in self.scannables.items()
        ])
        return out

    def _store_group(self, hdf_group: h5py.Group, path: str, name: str):

        nx_class = hdf_group.attrs.get('NX_class', 'Group')
        if hasattr(nx_class, 'decode'):
            nx_class = nx_class.decode()
        self.groups[path] = Group(
            nx_class,
            name,
            dict(hdf_group.attrs),
            [key for key, item in hdf_group.items() if isinstance(item, h5py.Dataset)]
        )
        self.classes[name].append(path)
        self.classes[nx_class].append(path)
        logger.debug(f"{path}  HDFGroup: {nx_class}")
        return nx_class

    def _store_dataset(self, hdf_dataset: h5py.Dataset, hdf_path: str, name: str):
        alt_name = generate_identifier(hdf_dataset.attrs[LOCAL_NAME]) if LOCAL_NAME in hdf_dataset.attrs else None
        self.datasets[hdf_path] = Dataset(name, hdf_dataset.size, hdf_dataset.shape, dict(hdf_dataset.attrs))
        if hdf_dataset.ndim >= 3:
            det_name = f"{hdf_path.split(SEP)[-2]}_{name}"
            self.image_data[name] = hdf_path
            self.image_data[det_name] = hdf_path
            self.arrays[name] = hdf_path
            if alt_name:
                self.arrays[alt_name] = hdf_path
            logger.debug(f"{hdf_path}  HDFDataset: image_data & array {name, hdf_dataset.size, hdf_dataset.shape}")
        elif hdf_dataset.ndim > 0:
            self.arrays[name] = hdf_path
            if alt_name:
                self.arrays[alt_name] = hdf_path
            logger.debug(f"{hdf_path}  HDFDataset: array {name, hdf_dataset.size, hdf_dataset.shape}")
        else:
            self.values[name] = hdf_path
            if alt_name:
                self.values[alt_name] = hdf_path
            logger.debug(f"{hdf_path}  HDFDataset: value")

    def _populate(self, hdf_group: h5py.Group, root: str = '',
                  recursive: bool = True, groups: list[str] = None):
        """
        populate HdfMap dictionary's using recursive method
        :param hdf_group: HDF group object, from HDF File
        :param root: str path of hdf Group, used to build dataset paths
        :param recursive: if True, will recursively search through subgroups
        :param groups: if not None, will only search subgroups named in list, e.g. ['entry','NX_DATA']
        :return: None
        """
        logger.info(f"{repr(self)}._populate root='{root}'")
        for key in hdf_group:
            obj = hdf_group.get(key)
            link = hdf_group.get(key, getlink=True)
            logger.debug(f"{key}: {repr(obj)} : {repr(link)}")
            if obj is None:
                continue  # dataset may be missing due to a broken link
            hdf_path = root + SEP + key  # build hdf path - a cross-file unique identifier
            name = generate_identifier(hdf_path)
            logger.info(f"{hdf_path}:  {name}, link={repr(link)}")

            # Group
            if isinstance(obj, h5py.Group):
                nx_class = self._store_group(obj, hdf_path, name)
                if recursive and (key in groups or nx_class in groups if groups else True):
                    self._populate(obj, hdf_path, recursive)

            # Dataset
            elif isinstance(obj, h5py.Dataset) and not isinstance(link, h5py.SoftLink):
                self._store_dataset(obj, hdf_path, name)

    def populate(self, hdf_file: h5py.File):
        """Populate all datasets from file"""
        self.filename = hdf_file.filename
        self._populate(hdf_file)
        size = self.most_common_size()
        self.generate_scannables(size)

    def generate_combined(self):
        self.combined = {**self.values, **self.arrays, **self.scannables}

    def most_common_size(self) -> int:
        """Return most common array size > 1"""
        array_sizes = [size for name, path in self.arrays.items() if (size := self.datasets[path].size) > 1]
        return max(set(array_sizes), key=array_sizes.count)

    def most_common_shape(self) -> tuple:
        """Return most common non-singular array shape"""
        array_shapes = [shape for name, path in self.arrays.items() if len(shape := self.datasets[path].shape) > 0]
        return max(set(array_shapes), key=array_shapes.count)

    def scannables_length(self) -> int:
        if not self.scannables:
            return 0
        path = next(iter(self.scannables.values()))
        shape = self.datasets[path].shape
        return shape[0]

    def generate_scannables(self, array_size):
        """Populate self.scannables field with datasets size that match array_size"""
        self.scannables = {k: v for k, v in self.arrays.items() if self.datasets[v].size == array_size}
        # create combined dict, scannables and arrays overwrite values with same name
        self.generate_combined()

    def generate_scannables_from_group(self, hdf_group: h5py.Group, group_path: str = None):
        """
        Generate scannables list from a specific group, using the first item to define array size
        :param hdf_group: h5py.Group
        :param group_path: str path of group hdf_group if hdf_group.name is incorrect
        """
        first_dataset = hdf_group[next(iter(hdf_group))]
        array_size = first_dataset.size
        # watch out - hdf_group.name may not point to a location in the file!
        hdf_path = hdf_group.name if group_path is None else group_path
        self._populate(hdf_group, root=hdf_path, recursive=False)
        self.scannables = {
            k: build_hdf_path(hdf_path, k)
            for k in hdf_group if isinstance(hdf_group[k], h5py.Dataset) and hdf_group[k].size == array_size
        }
        logger.debug(f"Scannables from group: {list(self.scannables.keys())}")
        self.generate_combined()

    def generate_scannables_from_names(self, names: list[str]):
        """Generate scannables list from a set of dataset names, using the first item to define array size"""
        # concert names or paths to name (to match alt_name)
        array_names = [n for name in names if (n := generate_identifier(name)) in self.arrays]
        logger.debug(f"Scannables from names: {array_names}")
        array_size = self.datasets[self.arrays[array_names[0]]].size
        self.scannables = {
            name: self.arrays[name] for name in array_names if self.datasets[self.arrays[name]].size == array_size
        }
        self.generate_combined()

    def get_path(self, name_or_path):
        """Return hdf path of object in HdfMap"""
        if name_or_path in self.datasets or name_or_path in self.groups:
            return name_or_path
        if name_or_path in self.combined:
            return self.combined[name_or_path]
        if name_or_path in self.image_data:
            return self.image_data[name_or_path]
        if name_or_path in self.classes:
            return self.classes[name_or_path][0]  # return first path in list

    def get_group_path(self, name_or_path):
        """Return group path of object in HdfMap"""
        hdf_path = self.get_path(name_or_path)
        while hdf_path and hdf_path not in self.groups:
            hdf_path = SEP.join(hdf_path.split(SEP)[:-1])
        if not hdf_path:
            return SEP
        return hdf_path

    def find_paths(self, string: str, name_only=True) -> list[str]:
        """
        Find any dataset paths that contain the given string argument
        :param string: str to find in list of datasets
        :param name_only: if True, search only the name of the dataset, not the full path
        :return: list of hdf paths
        """
        # find string in combined
        combined_paths = [path for name, path in self.combined.items() if string in name]
        if name_only:
            return [
                path for path, dataset in self.datasets.items()
                if string in dataset.name and path not in combined_paths
            ] + combined_paths
        return [
            path for path in self.datasets if string in path and path not in combined_paths
        ] + combined_paths

    def find_names(self, string: str) -> list[str]:
        """
        Find any dataset names that contain the given string argument, searching names in self.combined
        :param string: str to find in list of datasets
        :return: list of names
        """
        return [name for name in self.combined if string in name]

    def find_attr(self, attr_name: str) -> list[str]:
        """
        Find any dataset or group path with an attribute that contains attr_name.
        :param attr_name: str name of hdfobj.attr
        :return: list of hdf paths
        """
        return [
            path for path, (_, _, _, attr) in self.datasets.items() if attr_name in attr
        ] + [
            path for path, (_, _, attr, _) in self.groups.items() if attr_name in attr
        ]

    def get_attrs(self, name_or_path: str) -> dict:
        """Return attributes of dataset or group"""
        if name_or_path in self.datasets:
            return self.datasets[name_or_path].attrs
        if name_or_path in self.groups:
            return self.groups[name_or_path].attrs
        if name_or_path in self.combined:
            return self.datasets[self.combined[name_or_path]].attrs
        if name_or_path in self.classes:
            return self.groups[self.classes[name_or_path][0]].attrs

    def get_attr(self, name_or_path: str, attr_label: str, default: str | typing.Any = '') -> str:
        """Return named attribute from dataset or group, or default"""
        attrs = self.get_attrs(name_or_path)
        if attrs and attr_label in attrs:
            return attr.decode() if hasattr(attr := attrs[attr_label], 'decode') else attr
        return default

    def set_image_path(self, name_or_path: str):
        """Set the default image path, used by get_image"""
        if name_or_path is None:
            self._default_image_path = None
        else:
            path = self.get_path(name_or_path)
            if path:
                self._default_image_path = path
        logger.info(f"Default image path: {self._default_image_path}")

    def get_image_path(self) -> str | None:
        """Return HDF path of first dataset in self.image_data"""
        if self._default_image_path:
            return self._default_image_path
        if self.image_data:
            return next(iter(self.image_data.values()))

    def get_group_datasets(self, name_or_path: str) -> list[str] | None:
        """Find the path associate with the given name and return all datasets in that group"""
        group_path = self.get_group_path(name_or_path)
        if group_path:
            return self.groups[group_path].datasets

    "--------------------------------------------------------"
    "---------------------- FILE READERS --------------------"
    "--------------------------------------------------------"

    def get_data(self, hdf_file: h5py.File, name_or_path: str, index=(), default=None, direct_load=False):
        """
        Return data from dataset in file, converted into either datetime, str or squeezed numpy.array objects
        See hdfmap.eval_functions.dataset2data for more information.
        :param hdf_file: hdf file object
        :param name_or_path: str name or path pointing to dataset in hdf file
        :param index: index or slice of data in hdf file
        :param default: value to return if name not found in hdf file
        :param direct_load: return str, datetime or squeezed array if False, otherwise load data directly
        :return: dataset2data(dataset) -> datetime, str or squeezed array as required.
        """
        path = self.get_path(name_or_path)
        if path and path in hdf_file:
            return dataset2data(hdf_file[path], index, direct_load)
        return default

    def get_metadata(self, hdf_file: h5py.File, default=None, direct_load=False) -> dict:
        """Return metadata from file (values associated with hdfmap.values)"""
        extra = extra_hdf_data(hdf_file)
        metadata = {
            name: dataset2data(hdf_file[path], direct_load=direct_load) if path in hdf_file else default
            for name, path in self.values.items()
        }
        return {**extra, **metadata}

    def get_scannables(self, hdf_file: h5py.File) -> dict:
        """Return scannables from file (values associated with hdfmap.scannables)"""
        return {
            name: hdf_file[path][()] for name, path in self.scannables.items()
            if path in hdf_file
        }

    def get_image(self, hdf_file: h5py.File, index: slice = None) -> np.ndarray:
        """
        Get image data from file, using default image path
        :param hdf_file: hdf file object
        :param index: (slice,) or None to take the middle image
        :return: numpy array of image
        """
        if index is None:
            index = self.scannables_length() // 2
        image_path = self.get_image_path()
        logger.debug(f"image path: {image_path}")
        if image_path and image_path in hdf_file:
            return hdf_file[image_path][index].squeeze()  # remove trailing dimensions

    def _get_numeric_scannables(self, hdf_file: h5py.File) -> list[tuple[str, str]]:
        """Return numeric scannables available in file"""
        return [
            (name, path) for name, path in self.scannables.items()
            if hdf_file.get(path) and np.issubdtype(hdf_file.get(path).dtype, np.number)
        ]

    def get_scannables_array(self, hdf_file: h5py.File) -> np.ndarray:
        """Return 2D array of all scannables in file"""
        _scannables = self._get_numeric_scannables(hdf_file)
        dtypes = np.dtype([
            (name, hdf_file[path].dtype) for name, path in _scannables
        ])
        return np.array([hdf_file.get(path)[()] for name, path in _scannables], dtype=dtypes)

    def create_scannables_table(self, hdf_file: h5py.File, delimiter=', ',
                                string_spec='', format_spec='f', default_decimals=8) -> str:
        """
        Return str representation of scannables as a table
        The table starts with a header row given by names of the scannables.
        Each row contains the numeric values for each scannable, formated by the given string spec:
                {value: "string_spec.decimals format_spec"}
            e.g. {value: "5.8f"}
        decimals is taken from each scannables "decimals" attribute if it exits, otherwise uses default
        :param hdf_file: h5py.File object
        :param delimiter: str seperator between each column
        :param string_spec: str first element of float format specifier - length of string
        :param format_spec: str type element of format specifier - 'f'=float, 'e'=exponential, 'g'=general
        :param default_decimals: int default number of decimals given
        :return: str
        """
        _scannables = self._get_numeric_scannables(hdf_file)
        fmt = string_spec + '.%d' + format_spec
        formats = [
            '{:' + fmt % self.get_attr(path, 'decimals', default=default_decimals) + '}'
            for name, path in _scannables
        ]

        length = self.scannables_length()
        out = delimiter.join([name for name, _ in _scannables]) + '\n'
        out += '\n'.join([
            delimiter.join([
                fmt.format(hdf_file.get(path)[n])
                for (_, path), fmt in zip(_scannables, formats)
            ])
            for n in range(length)
        ])
        return out

    def get_dataholder(self, hdf_file: h5py.File) -> DataHolder:
        """
        Return DataHolder object - a simple replication of scisoftpy.dictutils.DataHolder
        Also known as DLS dat format.
            dataholder.scannable -> array
            dataholder.metadata.value -> metadata
            dataholder['scannable'] -> array
            dataholder.metadata['value'] -> metadata
        :param hdf_file: h5py.File object
        :return: data_object (similar to dict)
        """
        doc = f"""DataObject for '{hdf_file.filename}'"""
        metadata = self.get_metadata(hdf_file)
        scannables = self.get_scannables(hdf_file)
        scannables['metadata'] = DataHolder(metadata, docstr=doc)
        return DataHolder(scannables, docstr=doc)

    def eval(self, hdf_file: h5py.File, expression: str):
        """
        Evaluate an expression using the namespace of the hdf file
        :param hdf_file: h5py.File object
        :param expression: str expression to be evaluated
        :return: eval(expression)
        """
        return eval_hdf(hdf_file, expression, self.combined)

    def format_hdf(self, hdf_file: h5py.File, expression: str) -> str:
        """
        Evaluate a formatted string expression using the namespace of the hdf file
        :param hdf_file: h5py.File object
        :param expression: str expression using {name} format specifiers
        :return: eval_hdf(f"expression")
        """
        return format_hdf(hdf_file, expression, self.combined)

    def info_data(self, hdf_file):
        """Return string showing metadata values associated with names"""
        out = repr(self) + '\n'
        out = "Combined Namespace:\n"
        out += '\n'.join([
            f"{name:>30}: " +
            f"{str(data if np.size(data := dataset2data(hdf_file[path])) <= 1 else self.datasets[path].shape):20}" +
            f": {path:60}"
            for name, path in self.combined.items()
        ])
        out += f"\n{self.info_scannables()}"
        return out
