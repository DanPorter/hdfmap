import os
from time import perf_counter
import hdfmap


# Test all files in this folder
FOLDERS = [
    '/scratch/grp66007/data/i16/example',
    'C:/Users/grp66007/OneDrive - Diamond Light Source Ltd/I16/Nexus_Format/example_nexus'
]
# Folder with over 1000 files
THOUSAND_FILES = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/cm37262-1'
NFILES = 1332  # number of files to test (max 1332)
# FORMAT_STRING = """#{entry_identifier}\ncmd: {scan_command}\n"""
FORMAT_STRING = '#{entry_identifier}: {start_time} : E={incident_energy:.3f} keV : {scan_command}'


def check_nexus(*args, **kwargs):
    print(f"Opening: {args}, {kwargs}")
    mymap = hdfmap.create_nexus_map(*args, **kwargs)
    print(f"\n{repr(mymap)}")
    print(f"  N combined: {len(mymap.combined)}")
    print(f"N scannables: {len(mymap.scannables)}")
    print(f"      length: {mymap.scannables_length()}")
    print('HDF Paths:')
    print(f"scan_command: {mymap.get_path('scan_command')}")
    print(f"        axes: {mymap.get_path('axes')}")
    print(f"      signal: {mymap.get_path('signal')}")
    print(f"       image: {mymap.get_image_path()}")
    print('Data:')
    with hdfmap.load_hdf(mymap.filename) as hdf:
        cmd = mymap.get_data(hdf, 'scan_command')
        axes = mymap.get_data(hdf, 'axes')
        signal = mymap.get_data(hdf, 'signal')
        image = mymap.get_image(hdf, index=0)  # index=None finds some bad files where detector only contains 1 image
        print(f"scan_command: {cmd if cmd else None}")
        print(f"        axes: {axes.shape if axes is not None else None}")
        print(f"      signal: {signal.shape if signal is not None else None}")
        print(f"       image: {image.shape if image is not None else None}")
    print("---")
    return mymap


def test_files_in_folders():
    for folder in FOLDERS:
        if os.path.isdir(folder):
            files = hdfmap.list_files(folder)  # returns empty if folder doesn't exist
            for file in files:
                mymap = check_nexus(file)
                assert isinstance(mymap, hdfmap.NexusMap), f"{file} is not NexusMap"
        else:
            print(f"Skipping folder: {folder}")


def test_compare_time_for_many_files():
    files = hdfmap.list_files(THOUSAND_FILES)[:NFILES]
    # time to read single entry from each files
    start = perf_counter()
    output1 = []
    for file in files:
        with hdfmap.load_hdf(file) as hdf:
            output1.append((
                hdf['/entry1/scan_command'][()],
                hdf['/entry1/entry_identifier'][()],
                hdf['/entry1/start_time'][()],
                hdf['/entry1/sample/beam/incident_energy'][()],
            ))
    stop = perf_counter()
    single_time = stop - start

    # time to read multiple entries using hdfmap
    start = perf_counter()
    output2 = hdfmap.hdf_format(files, FORMAT_STRING)
    stop = perf_counter()
    multi_time = stop - start

    print(f"\nRead single entry from {len(files)} files in: {single_time:.3f} s")
    print(f"Read multi entry from {len(files)} files in: {multi_time:.3f} s")
    print(f"Performance factor: {((multi_time-single_time) / single_time):+.1%} of direct access time")
    # Typically around 40% slower
    assert multi_time < 1.5 * single_time, "mult-read is much slower than direct read"
