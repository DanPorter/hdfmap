"""
hdfmap example
"""

import hdfmap


def check_nexus(*args, **kwargs):
    mymap = hdfmap.create_nexus_map(*args, **kwargs)
    print(f"\n{repr(mymap)}")
    print(f"  N combined: {len(mymap.combined)}")
    print(f"N scannables: {len(mymap.scannables)}")
    print(f"      length: {mymap.scannables_length()}")
    print('Addresses:')
    print(f"scan_command: {mymap['scan_command']}")
    print(f"        axes: {mymap['axes']}")
    print(f"      signal: {mymap['signal']}")
    print(f"       image: {mymap.get_image_address()}")
    print('Data:')
    with hdfmap.load_hdf(mymap.filename) as hdf:
        cmd = mymap.get_data(hdf, 'scan_command')
        axes = mymap.get_data(hdf, 'axes')
        signal = mymap.get_data(hdf, 'signal')
        image = mymap.get_image(hdf)
        print(f"scan_command: {cmd if cmd else None}")
        print(f"        axes: {axes.shape if axes is not None else None}")
        print(f"      signal: {signal.shape if signal is not None else None}")
        print(f"       image: {image.shape if image is not None else None}")
    print("\n")
    return mymap


if __name__ == '__main__':
    # import os
    # check_nexus(os.path.dirname(__file__) + '/tests/data/1040323.nxs')
    # mymap = check_nexus('/dls/i06/data/2024/mm32821-10/i06-343988.nxs')
    mymap = check_nexus('/dls/science/groups/das/ExampleData/hdfmap_tests/i13/i13-1-368910.nxs')

    # from tkinter import filedialog
    #
    # filename = filedialog.askopenfilename(
    #     title='Select file to open',
    #     initialdir='/dls/i16/data',
    #     filetypes=[('NXS file', '.nxs'),
    #                ('HDF file', '.h5'), ('HDF file', '.hdf'), ('HDF file', '.hdf5'),
    #                ('All files', '.*')]
    # )
    # if filename:
    #     check_nexus(filename)

