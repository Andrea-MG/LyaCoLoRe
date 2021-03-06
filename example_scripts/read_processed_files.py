import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
import lya_mock_functions as mock
import sys

# main folder where the processed files are
basedir = '/Users/jfarr/Projects/repixelise/test_output/'
basedir += 'test_multi/'
nside = 8
pix = int(sys.argv[1])
pix_100 = int(pix/100)

dirname = basedir+'/'+str(pix_100)+'/'+str(pix)+'/'
suffix = str(nside)+'-'+str(pix)+'.fits'
print('dir name',dirname)

# file with physical density
phys_dens_file = dirname+'/physical-colore-'+suffix
print('physical density file',phys_dens_file)
phys_dens_hdu = fits.open(phys_dens_file)
phys_dens_hdu.info()
phys_dens_hdu.close()

# file with delta gaussian for picca
picca_gauss_file = dirname+'/picca-gaussian-'+suffix
print('picca gaussian file',picca_gauss_file)
picca_dens_hdu = fits.open(picca_gauss_file)
picca_dens_hdu.info()
picca_dens_hdu.close()

# file with Gaussian density
gauss_dens_file = dirname+'/gaussian-colore-'+suffix
print('gaussian density file',gauss_dens_file)
gauss_dens_hdu = fits.open(gauss_dens_file)
gauss_dens_hdu.info()
gauss_dens_hdu.close()

# file with delta density for picca
picca_dens_file = dirname+'/picca-density-'+suffix
print('picca density file',picca_dens_file)
picca_dens_hdu = fits.open(picca_dens_file)
picca_dens_hdu.info()
picca_dens_hdu.close()

# file with delta flux for picca
picca_flux_file = dirname+'/picca-flux-'+suffix
print('picca flux file',picca_flux_file)
picca_flux_hdu = fits.open(picca_flux_file)
picca_flux_hdu.info()
picca_flux_hdu.close()

# file with transmission for desisim
trans_flux_file = dirname+'/transmission-'+suffix
print('transmission flux file',trans_flux_file)
trans_flux_hdu = fits.open(trans_flux_file)
trans_flux_hdu.info()
trans_flux_hdu.close()
