import os
import shutil
import numpy as np
import xarray as xr
import pandas as pd
from ..convert import Convert

# raw_path = './echopype/data/azfp/17031001.01A'     # Canada (Different ranges)
# xml_path = './echopype/data/azfp/17030815.XML'     # Canada (Different ranges)
raw_path = './echopype/test_data/azfp/17082117.01A'     # Standard test
xml_path = './echopype/test_data/azfp/17041823.XML'     # Standard test
test_path = './echopype/test_data/azfp/from_matlab/17082117.nc'
# raw_path = ['./echopype/test_data/azfp/set1/' + file
#             for file in os.listdir('./echopype/test_data/azfp/set1')]
# xml_path = './echopype/test_data/azfp/set1/17033000.XML'       # Multiple files
csv_paths = ['./echopype/test_data/azfp/from_echoview/17082117-raw38.csv',    # EchoView exports
             './echopype/test_data/azfp/from_echoview/17082117-raw125.csv',
             './echopype/test_data/azfp/from_echoview/17082117-raw200.csv',
             './echopype/test_data/azfp/from_echoview/17082117-raw455.csv']


def test_convert_raw_matlab():

    # Unpacking data
    tmp = Convert(file=raw_path, model='AZFP', xml_path=xml_path)
    tmp.to_netcdf(overwrite=True)

    # Read in the dataset that will be used to confirm working conversions. (Generated by Matlab)
    ds_test = xr.open_dataset(test_path)

    # Test beam group
    with xr.open_dataset(tmp.output_path, group='Beam') as ds_beam:
        # Test frequency
        assert np.array_equal(ds_test.frequency, ds_beam.frequency)
        # Test sea absorption
        # assert np.array_equal(ds_test.sea_abs, ds_beam.sea_abs)
        # Test ping time
        assert np.array_equal(ds_test.ping_time, ds_beam.ping_time)
        # Test tilt x and y
        assert np.array_equal(ds_test.tilt_x, ds_beam.tilt_x)
        assert np.array_equal(ds_test.tilt_y, ds_beam.tilt_y)
        # Test backscatter_r
        assert np.array_equal(ds_test.backscatter, ds_beam.backscatter_r)

    # Test environment group
    with xr.open_dataset(tmp.output_path, group='Environment') as ds_env:
        # Test temperature
        assert np.array_equal(ds_test.temperature, ds_env.temperature)
        # Test sound speed. 1 value is used because sound speed is the same across frequencies
        # assert ds_test.sound_speed == ds_env.sound_speed_indicative.values[0]

    # with xr.open_dataset(tmp.output_path, group="Vendor") as ds_vend:
    #     # Test battery values
    #     assert np.array_equal(ds_test.battery_main, ds_vend.battery_main)
    #     assert np.array_equal(ds_test.battery_tx, ds_vend.battery_tx)

    ds_test.close()
    os.remove(tmp.output_path)
    del tmp


def test_convert_raw_echoview():
    # Compare parsed backscatter data with EchoView generated csv files.

    # Unpacking data
    tmp = Convert(file=raw_path, model='AZFP', xml_path=xml_path)
    tmp.to_netcdf()

    # Read in csv files that will be used to confirm working conversions.
    channels = []
    for file in csv_paths:
        channels.append(pd.read_csv(file, header=None, skiprows=[0]).iloc[:, 6:])
    test_power = np.stack(channels)
    with xr.open_dataset(tmp.output_path, group='Beam') as ds_beam:
        assert np.array_equal(test_power, ds_beam.backscatter_r)

    os.remove(tmp.output_path)


def test_convert_zarr():
    # Test saving zarr file. Compare with EchoView generated csv files.
    tmp = Convert(file=raw_path, model='AZFP', xml_path=xml_path)
    tmp.to_zarr()
    # Read in csv files that will be used to confirm working conversions.
    channels = []
    for file in csv_paths:
        channels.append(pd.read_csv(file, header=None, skiprows=[0]).iloc[:, 6:])
    test_power = np.stack(channels)
    with xr.open_zarr(tmp.output_path, group='Beam') as ds_beam:
        assert np.array_equal(test_power, ds_beam.backscatter_r)

    shutil.rmtree(tmp.output_path)


def test_validate_path():
    def compare_paths(p1, p2):
        assert os.path.normpath(p1) == os.path.normpath(p2)

    # Construct file path strings
    tmp = Convert(file=raw_path, model='AZFP', xml_path=xml_path)
    base_dir, base_filename = os.path.split(raw_path)
    new_filename = base_filename[:-4] + '.nc'
    directory = os.path.join(base_dir, 'temp_test_folder')
    filename = 'test.nc'
    file_path = os.path.join(directory, filename)

    # Test saving
    # save_path is None
    tmp._validate_path(file_format='.nc')
    compare_paths(tmp.output_path[0], raw_path[:-3] + 'nc')
    # save_path is directory
    tmp._validate_path(file_format='.nc', save_path=directory)
    compare_paths(tmp.output_path[0], os.path.join(directory, new_filename))
    # Check if the requested folder is created
    assert os.path.exists(directory)
    # save_path is just a filename
    tmp._validate_path(file_format='.nc', save_path=filename)
    compare_paths(tmp.output_path[0], os.path.join(base_dir, filename))
    # save_path is a file path
    tmp._validate_path(file_format='.nc', save_path=file_path)
    compare_paths(tmp.output_path[0], file_path)
    # save_path is a file that does not match the extension of file_format (should fail)
    try:
        tmp._validate_path(file_format='.zarr', save_path=file_path)
    except ValueError:
        pass
    else:
        raise AssertionError
    # test unsupported file format (should fail)
    try:
        tmp._validate_path(file_format='.csv', save_path=file_path[:-3] + '.csv')
    except ValueError:
        pass
    else:
        raise AssertionError
    # save_path is a file when there are multiple input files (Should fail)
    tmp.set_source(file=[raw_path, raw_path], model='AZFP', xml_path=xml_path)
    try:
        tmp._validate_path(file_format='.nc', save_path=file_path)
    except ValueError:
        pass
    else:
        raise AssertionError

    os.rmdir(directory)
