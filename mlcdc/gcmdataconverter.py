from os.path import join
import numpy as np
import xarray as xr
import zarr

#from .data_utils import (open_full_dataset,
#        #,educe_vertical_levels, get_vertical_coordinates,
#        #get_wind_speed, get_srf_current_speed, get_sst, get_ast
#        )

class GCMDataConverter():
    """Convert GCM output to dataset with features and labels, save as zarr store
    GCM output is expected to have dimensions:

        ('ens_mem', 'atm_lev', 'ocn_lev', 'lat', 'lon')


    Attributes:
        label_nc_fname (str): path to netcdf dataset with labels (correlations)
        labelname (str): name of field in dataset that denotes correlation field
        gcm_nc_dir (str): directory containing multiple netcdf files, one per ensemble member
        rename (dict): denoting how variable names are to be renamed
        coarsen (dict): how to coarsen the dataset, e.g. average ensemble members over N members
        chunks (dict): chunking scheme for zarr store
        zstore_dir (str): directory inside of which to save zarr store
        keep_vars (list of str): field names to keep in feature dataset
        ocn_2d_vars (list of str): 2D oceanic fields, remove extraneous vertical coordinate. These variables must be in :attr:`keep_vars`
    """
    label_nc_fname = '/work2/noaa/gsienkf/tsmith/mlcdc/data/temperature_cross_correlations_averaged.nc'
    labelname = "corr_atm_ocn"
    gcm_nc_dir = '/work2/noaa/gsienkf/weihuang/WCLEKF_PRODFORECAST/20151205000000/latlongrid-20151206.030000/AtmOcnIce/'

    rename = {
            'ens_mem'   : 'member',
            'atm_lev'   : 'alev',
            'ocn_lev'   : 'olev'}

    coarsen = {
            'member'    : 20}

    chunks = {
            'lon'       : 10,
            'lat'       : 10,
            'alev'      : -1,
            'olev'      : -1,
            'member'    : -1}

    zstore_dir = './'

    keep_vars = ['atm_u', 'atm_v', 'atm_W', 'atm_DZ', 'atm_T', 'atm_delp', 'atm_phis', 'atm_t2m', 'atm_q2m', 'atm_tprcp', 'atm_qrain', 'atm_sphum', 'atm_liq_wat', 'atm_rainwat', 'atm_ice_wat', 'atm_snowwat', 'atm_cld_amt', 'atm_u_srf', 'atm_v_srf', 'atm_totprcp_ave', 'atm_cnvprcp_ave', 'ocn_Temp', 'ocn_Salt', 'ocn_h', 'ocn_u', 'ocn_v', 'ocn_frazil', 'ocn_ave_ssh', 'ocn_sfc', 'ocn_u2', 'ocn_v2', 'ocn_h2', 'ocn_uh', 'ocn_vh', 'ocn_diffu', 'ocn_diffv', 'ocn_ubtav', 'ocn_vbtav', 'ocn_MEKE', 'ocn_MEKE_Kh', 'ocn_MLD', 'ocn_MLD_MLE_filtered', 'atm_slmsk']
    ocn_2d_vars = ['ocn_MLD', 'ocn_MLD_MLE_filtered', 'ocn_MEKE', 'ocn_MEKE_Kh', 'ocn_sfc', 'ocn_frazil', 'ocn_ave_ssh']

    @property
    def zstore_path(self):
        cstr = ".".join([f"{v:02d}{k}" for k, v in self.chunks.items()])
        return join(self.zstore_dir, f"tcorr.predictors0.{cstr}.zarr")


    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


    def __call__(self):

        ds = self.get_predictors()

        ds[self.labelname] = self.get_labels()

        ds = self.apply_mask(ds)

        self.saveit(ds)


    def get_labels(self):
        """Get the field/array with labels from netcdf file
        Returns:
            xda (:obj:`xarray.DataArray`): the field of labels (correlation)
        """
        xds = xr.open_dataset(self.label_nc_fname)
        return xds[self.labelname]


    def get_predictors(self):
        """Get the predictors/features from gcm nc files

        Returns:
            xds (:obj:`xarray.Dataset`): With all features/predictors as data variables
        """

        xds = open_full_dataset(self.gcm_nc_dir)
        xds = reduce_vertical_levels(xds)
        xds = xds[self.keep_vars]
        xds = get_vertical_coordinates(xds)

        # This keeps attrs
        xds[self.ocn_2d_vars] = xds[self.ocn_2d_vars].sel(ocn_lev=1)

        xds['atm_wind_speed'] = np.sqrt(xds['atm_u']**2 + xds['atm_v']**2)
        xds['atm_wind_speed'].attrs = {'long_name': 'Atmospheric wind speed (derived)',
                                       'units': xds['atm_u'].units}


        xds['ocn_speed'] = np.sqrt(xds['ocn_u']**2 + xds['ocn_v']**2)
        xds['ocn_speed'].attrs = {'long_name': 'Ocean current speed (derived)',
                                  'units': xds['ocn_u'].units}

        xds = get_sst(xds)
        xds = get_ast(xds)
        return xds


    @staticmethod
    def apply_mask(xds):
        """Get boolean mask denoting ocean only points.
        Apply this mask so that points that are not "ocean-only" for all ensemble
        members become NaN.

        According to random pdf on the internet, atm_slmsk values have the following meaning:
            0 : ocean
            1 : land
            2 : seaice

        Args:
            xds (:obj:`xarray.Dataset`): apply mask to all data variables in this xarray dataset

        Returns:
            xds (:obj:`xarray.Dataset`): with mask applied
        """

        mask = (xds['atm_slmsk'] == 0).all('ens_mem')
        for key in xds.data_vars:
            xds[key] = xds[key].where(mask)

        xds['ocn_mask'] = mask
        xds['ocn_mask'].attrs = {'Description': 'True where points are ocean only (atm_slmsk==0) for all ensemble members'}

        return xds


    def rechunk(self, xds):
        """Apply encoding workaround and chunk
        Not clear if this encoding workaround is necessary for this xarray version ... oh well

        Args:
            xds (:obj:`xarray.Dataset`): xarray dataset to rechunk
        """

        for key in xds.data_vars:
            xds[key].encoding={}

        return xds.chunk(self.chunks)


    def saveit(self, xds):
        """Apply renaming, coarsen, and chunking. Then save dataset to a zarr store.

        Args:
            xds (:obj:`xarray.Dataset`): xarray dataset to save
        """

        xds = xds.rename(self.rename)
        xds = xds.coarsen(self.coarsen, boundary='exact').mean()
        xds = self.rechunk(xds)

        store = zarr.NestedDirectoryStore(path=self.zstore_path)
        xds.to_zarr(store=store)
        print(f"Saved zarr store at: {self.zstore_path}")


if __name__ == "__main__":

    do = DataOrganizer(zstore_dir="/work2/noaa/gsienkf/tsmith/mlcdc/data/")
    do()
