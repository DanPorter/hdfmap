"""
hdfmap class definition
"""
import typing

import numpy as np
import h5py

from .eval_functions import extra_hdf_data, eval_hdf, format_hdf

try:
    import hdf5plugin  # required for compressed data
except ImportError:
    print('Warning: hdf5plugin not available.')

# parameters
SEP = '/'  # HDF address separator


def address2name(address: str | bytes) -> str:
    """Convert hdf address to name"""
    if hasattr(address, 'decode'):  # Byte string
        address = address.decode('ascii')
    address = address.replace('.', '_')  # remove dots as cant be evaluated
    # address = address.split('.')[-1]  # alternative to replacing dots
    name = address.split(SEP)[-1]
    return address.split(SEP)[-1] if name == 'value' else name


def build_address(*args: str | bytes) -> str:
    """
    Build address from string or bytes arguments
        '/entry/measurement' = build_address(b'entry', 'measurement')
    :param args: str or bytes arguments
    :return: str address
    """
    return SEP + SEP.join((arg.decode() if isinstance(arg, bytes) else arg).strip(SEP) for arg in args)


def _disp_dict(mydict: dict, indent: int = 10) -> str:
    return '\n'.join([f"{key:>{indent}}: {value}" for key, value in mydict.items()])


class _DictObj(dict):
    """
    Convert dict to class that looks like a class object with key names as attributes
        obj = DictObj({'item1': 'value1'}, 'docs')
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


class HdfMap:
    """
    HdfMap object, container for addresses of different objects in an HDF file
        map = HdfMap()
        with h5py.File('file.hdf') as hdf:
            map.populate(hdf)
        size = map.most_common_size()
        map.generate_scannables(size)

        map.get_address('data') -> '/entry/measurement/data'
        map['data'] -> '/entry/measurement/data'

        with h5py.File('another_file.hdf') as hdf:
            data = map.get_data(hdf, 'data')
            array = map.get_scannables_array(hdf)
            metadata = map.get_metadata(hdf)
            out = map.eval(hdf, 'data / 10')
            outstr = map.format(hdf, 'the data looks like: {data}')

    Objects within the HDF file are separated into Groups and Datasets. Each object has a
    defined 'address' and 'name' paramater, as well as other attributes
        address -> '/entry/measurement/data' -> the location of an object within the file
        name -> 'data' -> an address expressed as a simple variable name
    Address are unique location within the file but can be used to identify similar objects in other files
    Names may not be unique within a file and are generated from the address.

    Names of different types of datasets are stored for arrays (size > 0) and values (size 0)
    Names for scannables relate to all arrays of a particular size
    A combined list of names is provided where scannables > arrays > values

    Attributes:
        map.groups      stores attributes of each group by address
        map.classes     stores list of group addresses by nx_class
        map.datasets    stores attributes of each dataset by address
        map.arrays      stores array dataset addresses by name
        map.values      stores value dataset addresses by name
        map.scannables  stores array dataset addresses with given size, by name
        map.combined    stores array and value addresses (arrays overwrite values)
        map.image_data  stores dataset addresses of image data
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
        map.get_size('name_or_address') -> return dataset size
        map.get_shape('name_or_address') -> return dataset size
        map.get_attr('name_or_address', 'attr') -> return value of dataset attribute
        map.get_address('name_or_group_or_class') -> returns address of object with name
        map.get_image_address() -> returns default address of detector dataset (or largest dataset)
        map.get_group_address('name_or_address_or_class') -> return address of group with class
        map.get_group_datasets('name_or_address_or_class') -> return list of dataset addresses in class
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
    _debug_logger = print

    def __init__(self):
        self._debug = False
        self.filename = ''
        self.groups = {}  # stores attributes of each group by address
        self.classes = {}  # stores group addresses by nx_class
        self.datasets = {}  # stores attributes of each dataset by address
        self.arrays = {}  # stores array dataset addresses by name
        self.values = {}  # stores value dataset addresses by name
        self.scannables = {}  # stores array dataset addresses with given size, by name
        self.combined = {}  # stores array and value addresses (arrays overwrite values)
        self.image_data = {}  # stores dataset addresses of image data
        self._default_image_address = None

    def __getitem__(self, item):
        # TODO: make this work correctly for __contains__, __getitem__ and __iter__
        return self.combined[item]

    def __repr__(self):
        return f"HdfMap based on '{self.filename}'"

    def info_groups(self):
        """Return str info on groups"""
        out = f"{repr(self)}\n"
        out += "Groups:\n"
        out += _disp_dict(self.groups, 10)
        out += '\n\nClasses:\n'
        out += _disp_dict(self.classes, 10)
        return out

    def info_datasets(self):
        """Return str info on datasets"""
        out = f"{repr(self)}\n"
        out += "Datasets:\n"
        out += _disp_dict(self.datasets, 10)
        return out

    def info_dataset_types(self):
        """Return str info on dataset types"""
        out = "Values:\n"
        out += _disp_dict(self.values, 10)
        out += "Arrays:\n"
        out += '\n'.join([
            f"{name:>10}: {str(self.datasets[address][2]):10} : {address:60}"
            for name, address in self.arrays.items()
        ])
        out += "Images:\n"
        out += '\n'.join([
            f"{name:>10}: {str(self.datasets[address][2]):10} : {address:60}"
            for name, address in self.image_data.items()
        ])
        return out

    def info_names(self):
        """Return str info on combined namespace"""
        out = "Combined Namespace:\n"
        out += '\n'.join([
            f"{name:>10}: {str(self.datasets[address][2]):10} : {address:60}"
            for name, address in self.combined.items()
        ])
        return out

    def info_scannables(self):
        """Return str info on scannables namespace"""
        out = "Scannables Namespace:\n"
        out += '\n'.join([
            f"{name:>10}: {str(self.datasets[address][2]):10} : {address:60}"
            for name, address in self.scannables.items()
        ])
        return out

    def __str__(self):
        return f"{repr(self)}\n{self.info_names()}\n"

    def debug(self, state=True, logger_function=None):
        """Turn debugging on"""
        self._debug = state
        if logger_function:
            self._debug_logger = logger_function

    def _load_defaults(self, hdf_file: h5py.File):
        """Overloaded method, called before _populate"""

    def _store_group(self, hdf_group: h5py.Group, address: str, name: str):
        try:
            nx_class = hdf_group.attrs['NX_class'].decode() if 'NX_class' in hdf_group.attrs else 'Group'
        except AttributeError:
            nx_class = hdf_group.attrs['NX_class']
        except OSError:
            nx_class = 'NoClass'  # if object doesn't have attrs
        # TODO: replace groups tuple with Group class
        self.groups[address] = (
            nx_class,
            name,
            dict(hdf_group.attrs),
            [key for key in hdf_group.keys() if isinstance(hdf_group.get(key), h5py.Dataset)]
        )
        if name not in self.classes:
            self.classes[name] = [address]
        else:
            self.classes[name].append(address)
        if nx_class not in self.classes:
            self.classes[nx_class] = [address]
        else:
            self.classes[nx_class].append(address)
        if self._debug:
            self._debug_logger(f"{address}  HDFGroup: {nx_class}")
        return nx_class

    def _store_dataset(self, hdf_dataset: h5py.Dataset, address: str, name: str, altname: str):
        # TODO: replace datasets tuple with Dataset class
        self.datasets[address] = (name, hdf_dataset.size, hdf_dataset.shape, dict(hdf_dataset.attrs))
        if hdf_dataset.ndim >= 3:
            det_name = f"{address.split(SEP)[-2]}_{name}"
            self.image_data[name] = address
            self.image_data[det_name] = address
            self.arrays[name] = address
            self.arrays[altname] = address
            if self._debug:
                self._debug_logger(
                    f"{address}  HDFDataset: image_data & array {name, hdf_dataset.size, hdf_dataset.shape}"
                )
        elif hdf_dataset.ndim > 0:
            self.arrays[name] = address
            self.arrays[altname] = address
            if self._debug:
                self._debug_logger(f"{address}  HDFDataset: array {name, hdf_dataset.size, hdf_dataset.shape}")
        else:
            self.values[name] = address
            self.values[altname] = address
            if self._debug:
                self._debug_logger(f"{address}  HDFDataset: value")

    def _populate(self, hdf_group: h5py.Group, top_address: str = '',
                  recursive: bool = True, groups: list[str] = None):
        """
        populate HdfMap dictionary's using recursive method
        :param hdf_group: HDF group object, from HDF File
        :param top_address: str address of hdf Group, used to build dataset addresses
        :param recursive: if True, will recursively search through subgroups
        :param groups: if not None, will only search subgroups named in list, e.g. ['entry','NX_DATA']
        :return: None
        """
        for key in hdf_group:
            obj = hdf_group.get(key)
            link = hdf_group.get(key, getlink=True)
            if self._debug:
                self._debug_logger(f"{key}: {repr(obj)} : {repr(link)}")
            if obj is None:
                continue  # dataset may be missing due to a broken link
            address = top_address + SEP + key  # build hdf address - a cross-file unique identifier
            name = address2name(address)
            altname = address2name(obj.attrs['local_name']) if 'local_name' in obj.attrs else name
            if self._debug:
                self._debug_logger(f"{address}  {name}, altname={altname}, link={repr(link)}")

            # Group
            if isinstance(obj, h5py.Group):
                nx_class = self._store_group(obj, address, name)
                if recursive and (key in groups or nx_class in groups if groups else True):
                    self._populate(obj, address, recursive)

            # Dataset
            elif isinstance(obj, h5py.Dataset) and not isinstance(link, h5py.SoftLink):
                self._store_dataset(obj, address, name, altname)

    def populate(self, hdf_file: h5py.File):
        """Populate all datasets from file"""
        self.filename = hdf_file.filename
        self._load_defaults(hdf_file)
        self._populate(hdf_file)

    def generate_combined(self):
        self.combined = {**self.values, **self.arrays, **self.scannables}

    def most_common_size(self) -> int:
        """Return most common array size > 1"""
        array_sizes = [
            self.datasets[address][1]
            for name, address in self.arrays.items()
            if self.datasets[address][1] > 1
        ]
        return max(set(array_sizes), key=array_sizes.count)

    def most_common_shape(self) -> tuple:
        """Return most common non-singular array shape"""
        array_shapes = [
            self.datasets[address][2]
            for name, address in self.arrays.items()
            if len(self.datasets[address][2]) > 0
        ]
        return max(set(array_shapes), key=array_shapes.count)

    def scannables_length(self) -> int:
        if not self.scannables:
            return 0
        address = next(iter(self.scannables.values()))
        shape = self.datasets[address][2]
        return shape[0]

    def generate_scannables(self, array_size):
        """Populate self.scannables field with datasets size that match array_size"""
        self.scannables = {k: v for k, v in self.arrays.items() if self.datasets[v][1] == array_size}
        # create combined dict, scannables and arrays overwrite values with same name
        self.generate_combined()

    def generate_scannables_from_group(self, hdf_group: h5py.Group, group_address: str = None):
        """
        Generate scannables list from a specific group, using the first item to define array size
        :param hdf_group: h5py.Group
        :param group_address: str address of group hdf_group if hdf_group.name is incorrect
        """
        first_dataset = hdf_group[next(iter(hdf_group.keys()))]
        array_size = first_dataset.size
        # watch out - hdf_group.name may not point to a location in the file!
        address = hdf_group.name if group_address is None else group_address
        self._populate(hdf_group, top_address=address, recursive=False)
        self.scannables = {
            k: build_address(address, k)
            for k in hdf_group if isinstance(hdf_group[k], h5py.Dataset) and hdf_group[k].size == array_size
        }
        self.generate_combined()

    def generate_scannables_from_names(self, names: list[str]):
        """Generate scannables list from a set of dataset names, using the first item to define array size"""
        # concert names or addresses to name (to match altname)
        array_names = [address2name(name) for name in names if address2name(name) in self.arrays]
        if self._debug:
            self._debug_logger(f"Scannables from names: {array_names}")
        array_size = self.datasets[self.arrays[array_names[0]]][1]
        self.scannables = {
            name: self.arrays[name] for name in array_names if self.datasets[self.arrays[name]][1] == array_size
        }
        self.generate_combined()

    def _get_dataset(self, name_or_address: str, idx: int):
        """Return attribute of dataset"""
        if name_or_address in self.datasets:
            return self.datasets[name_or_address][idx]
        if name_or_address in self.combined:
            return self.datasets[self.combined[name_or_address]][idx]

    def get_address(self, name_or_address):
        """Return address of object in HdfMap"""
        if name_or_address in self.datasets or name_or_address in self.groups:
            return name_or_address
        if name_or_address in self.combined:
            return self.combined[name_or_address]
        if name_or_address in self.image_data:
            return self.image_data[name_or_address]
        if name_or_address in self.classes:
            return self.classes[name_or_address][0]

    def get_group_address(self, name_or_address):
        """Return group address of object in HdfMap"""
        address = self.get_address(name_or_address)
        while address and address not in self.groups:
            address = SEP.join(address.split(SEP)[:-1])
        return address

    def find(self, name: str, name_only=True) -> list[str]:
        """
        Search for name in addresses, return list of hdf addresses
        :param name: str to find in list of datasets
        :param name_only: if True, search only the name of the dataset, not the full address
        :return: list of hdf addresses
        """
        if name_only:
            return [
                address for address, (dataset_name, size, shape, attrs) in self.datasets.items()
                if name in dataset_name
            ]
        return [address for address in self.datasets if name in address]

    def find_attr(self, attr_name: str) -> list[str]:
        """
        Search for hdf objects with a particular attribute (checks datasets and groups for obj.attr[name])
        :param attr_name: str name of hdfobj.attr
        :return: list of hdf addresses
        """
        return [
            address for address, (_, _, _, attr) in self.datasets.items() if attr_name in attr
        ] + [
            address for address, (_, _, attr, _) in self.groups.items() if attr_name in attr
        ]

    def get_size(self, name_or_address: str) -> int:
        """Return size of dataset"""
        return self._get_dataset(name_or_address, 1)

    def get_shape(self, name_or_address: str) -> tuple:
        """Return shape of dataset"""
        return self._get_dataset(name_or_address, 2)

    def get_attrs(self, name_or_address: str) -> dict:
        """Return attributes of dataset or group"""
        if name_or_address in self.datasets:
            return self.datasets[name_or_address][3]
        if name_or_address in self.groups:
            return self.groups[name_or_address][2]
        if name_or_address in self.combined:
            return self.datasets[self.combined[name_or_address]][3]
        if name_or_address in self.classes:
            return self.groups[self.classes[name_or_address][0]][2]

    def get_attr(self, name_or_address: str, attr_label: str, default: str | typing.Any = '') -> str:
        """Return named attribute from dataset or group, or default"""
        attrs = self.get_attrs(name_or_address)
        if attr_label in attrs:
            return attrs[attr_label]
        return default

    def set_image_address(self, name_or_address: str):
        """Set the default image address, used by get_image"""
        if name_or_address is None:
            self._default_image_address = None
        else:
            address = self.get_address(name_or_address)
            if address:
                self._default_image_address = address
        if self._debug:
            self._debug_logger(f"Default image address: {self._default_image_address}")

    def get_image_address(self) -> str:
        """Return HDF address of first dataset in self.image_data"""
        if self._default_image_address:
            return self._default_image_address
        if self.image_data:
            return next(iter(self.image_data.values()))

    def get_group_datasets(self, name_or_address: str) -> list[str]:
        """Find the address associate with the given name and return all datasets in that group"""
        group_address = self.get_group_address(name_or_address)
        if group_address:
            return self.groups[group_address][3]

    "--------------------------------------------------------"
    "---------------------- FILE READERS --------------------"
    "--------------------------------------------------------"

    def get_data(self, hdf_file: h5py.File, name_or_address: str, index=(), default=None):
        """Return data from dataset in file"""
        address = self.get_address(name_or_address)
        if address and address in hdf_file:
            return hdf_file[address][index]
        return default

    def get_metadata(self, hdf_file: h5py.File, default=None) -> dict:
        """Return metadata from file (values associated with hdfmap.values)"""
        extra = extra_hdf_data(hdf_file)
        metadata = {
            name: hdf_file[address][()] if address in hdf_file else default
            for name, address in self.values.items()
        }
        return {**extra, **metadata}

    def get_scannables(self, hdf_file: h5py.File) -> dict:
        """Return scannables from file (values associated with hdfmap.scannables)"""
        return {
            name: hdf_file[address][()] for name, address in self.scannables.items()
            if address in hdf_file
        }

    def get_image(self, hdf_file: h5py.File, index: slice = None) -> np.ndarray:
        """
        Get image data from file, using default image address
        :param hdf_file: hdf file object
        :param index: (slice,) or None to take the middle image
        :return: numpy array of image
        """
        if index is None:
            index = self.scannables_length() // 2
        image_address = self.get_image_address()
        if self._debug:
            self._debug_logger(f"image address: {image_address}")
        if image_address and image_address in hdf_file:
            return hdf_file[image_address][index].squeeze()  # remove trailing dimensions

    def _get_numeric_scannables(self, hdf_file: h5py.File) -> list[tuple[str, str]]:
        """Return numeric scannables available in file"""
        return [
            (name, address) for name, address in self.scannables.items()
            if hdf_file.get(address) and np.issubdtype(hdf_file.get(address).dtype, np.number)
        ]

    def get_scannables_array(self, hdf_file: h5py.File) -> np.ndarray:
        """Return 2D array of all scannables in file"""
        _scannables = self._get_numeric_scannables(hdf_file)
        dtypes = np.dtype([
            (name, hdf_file[address].dtype) for name, address in _scannables
        ])
        return np.array([hdf_file.get(address)[()] for name, address in _scannables], dtype=dtypes)

    def get_scannables_str(self, hdf_file: h5py.File, delimiter=', ',
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
            '{:' + fmt % self.get_attr(address, 'decimals', default=default_decimals) + '}'
            for name, address in _scannables
        ]

        length = self.scannables_length()
        out = delimiter.join([name for name, _ in _scannables]) + '\n'
        out += '\n'.join([
            delimiter.join([
                fmt.format(hdf_file.get(address)[n])
                for (_, address), fmt in zip(_scannables, formats)
            ])
            for n in range(length)
        ])
        return out

    def get_data_block(self, hdf_file: h5py.File) -> _DictObj:
        """
        Return data object
            data_object.scannable -> array
            data_object.metadata.value -> metadata
            data_object['scannable'] -> array
            data_object.metadata['value'] -> metadata
        :param hdf_file: h5py.File object
        :return: data_object (similar to dict)
        """
        doc = f"""DataObject for '{hdf_file.filename}'"""
        metadata = self.get_metadata(hdf_file)
        scannables = self.get_scannables(hdf_file)
        scannables['metadata'] = _DictObj(metadata, docstr=doc)
        return _DictObj(scannables, docstr=doc)

    def eval(self, hdf_file: h5py.File, expression: str):
        """
        Evaluate an expression using the namespace of the hdf file
        :param hdf_file: h5py.File object
        :param expression: str expression to be evaluated
        :return: eval(expression)
        """
        return eval_hdf(hdf_file, expression, self.combined, self._debug)

    def format_hdf(self, hdf_file: h5py.File, expression: str) -> str:
        """
        Evaluate a formatted string expression using the namespace of the hdf file
        :param hdf_file: h5py.File object
        :param expression: str expression using {name} format specifiers
        :return: eval_hdf(f"expression")
        """
        return format_hdf(hdf_file, expression, self.combined, self._debug)
