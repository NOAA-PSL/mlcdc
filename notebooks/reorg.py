#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import xarray as xr


def get_labels(chunks):
    ds = xr.open_dataset('/work2/noaa/gsienkf/tsmith/mlcdc/data/temperature_cross_correlations_averaged.nc')
    ds = ds.stack(x=('lon','lat'))


    ds = ds.chunk(chunks)
    ds = ds.reset_index('x')
    ds.to_zarr('/work2/noaa/gsienkf/tsmith/mlcdc/data/temperature.correlations.avg.74alev.44olev.10x.zarr', mode='w')

def get_predictors(chunks):

    import sys
    sys.path.insert(0, '/work/noaa/gsienkf/zstanley/projects/mlcdc/notebooks/')
    from load_data_fns import (
            open_full_dataset, reduce_vertical_levels, get_vertical_coordinates,
            get_sst, get_ast )

    proj_dir = '/work/noaa/gsienkf/zstanley/projects/mlcdc/'
    data_dir = '/work2/noaa/gsienkf/weihuang/WCLEKF_PRODFORECAST/20151205000000/latlongrid-20151206.030000/AtmOcnIce/'

    keep_vars = ['atm_u', 'atm_v', 'atm_W', 'atm_DZ', 'atm_T', 'atm_liq_wat', 'atm_delp', 'atm_sphum', 'atm_cld_amt',
             'ocn_Temp', 'ocn_h', 'ocn_u', 'ocn_v']
    ocn_2d_vars = ['ocn_MLD', 'ocn_MEKE', 'ocn_sfc', 'ocn_ave_ssh']


    ds = open_full_dataset(data_dir)
    ds = reduce_vertical_levels(ds)

    ds = ds[keep_vars+ocn_2d_vars]

    ds = get_vertical_coordinates(ds)

    ds[ocn_2d_vars] = ds[ocn_2d_vars].sel(ocn_lev=1)

    ds['atm_wind_speed'] = np.sqrt(ds['atm_u']**2 + ds['atm_v']**2)
    ds['atm_wind_speed'].attrs = {'long_name': 'Atmospheric wind speed (derived)',
                                  'units': ds['atm_u'].units}


    ds['ocn_srf_speed'] = np.sqrt(ds['ocn_u']**2 + ds['ocn_v']**2)
    ds['ocn_srf_speed'].attrs = {'long_name': 'Ocean current speed (derived)',
                                  'units': ds['ocn_u'].units}


    ds = get_sst(ds)
    ds = get_ast(ds)

    # Stack x
    ds = ds.stack(x=('lon','lat'))
    ds = ds.reset_index('x')

    # avg by chunked ensemble member
    ds = ds.coarsen({'ens_mem': 20}, boundary='exact').mean()

    # Rename to sample? we'll see what notation sticks
    ds = ds.rename({'ens_mem': 'sample'})

    # Chunk
    chunks['sample'] = -1
    for key in ds.data_vars:
        ds[key].encoding={}
    ds = ds.chunk(chunks)

    ds.to_zarr('/work2/noaa/gsienkf/tsmith/mlcdc/data/predictors0.04sample.74alev.44olev.10x.zarr')


if __name__ == "__main__":

    chunks = {'x': 10,
              'atm_lev': -1,
              'ocn_lev': -1}

    #get_labels(chunks)

    get_predictors(chunks)
