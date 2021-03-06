import numpy as np
from astropy.io import fits
import healpy as hp
import os
import time
import fast_prng
import DLA
import matplotlib.pyplot as plt

#My modules
import RSD

#DLA imports:
from scipy.stats import norm
from scipy.interpolate import interp1d, interp2d
import astropy.table

# TODO: remove SIGMA_G from the headers of the saved files as it cannot be relied upon.

lya = 1215.67

#Function to create a 'simulation_data' object given a specific pixel, information about the complete simulation, and the location/filenames of data files.
def make_gaussian_pixel_object(pixel,original_file_location,original_filename_structure,input_format,MOCKID_lookup,lambda_min=0,IVAR_cutoff=lya):

    #Determine which file numbers we need to look at for the current pixel.
    relevant_keys = [key for key in MOCKID_lookup.keys() if key[1]==pixel]
    files_included = 0

    #For each relevant file, extract the data and aggregate over all files into a 'combined' object.
    for key in relevant_keys:
        #Get the MOCKIDs of the relevant quasars: those that are located in the current pixel, stored in the current file.
        file_number = key[0]
        relevant_MOCKIDs = MOCKID_lookup[key]
        N_relevant_qso = len(relevant_MOCKIDs)

        #If there are some relevant quasars, open the data file and make it into a simulation_data object.
        #We use simulation_data.get_reduced_data to avoid loading all of the file's data into the object.
        if N_relevant_qso > 0:
            filename = original_file_location + '/' + original_filename_structure.format(file_number)
            working = simulation_data.get_gaussian_skewers_object(filename,file_number,input_format,MOCKIDs=relevant_MOCKIDs,lambda_min=lambda_min,IVAR_cutoff=IVAR_cutoff)

        #Combine the data from the working file with that from the files already looked at.
        if files_included > 0:
            combined = simulation_data.combine_files(combined,working,gaussian_only=True)
            files_included += 1
        else:
            combined = working
            files_included += 1

    pixel_object = combined

    return pixel_object

#general.py
#Function to create a file structure based on a set of numbers, of the form "x//100"/"x".
def make_file_structure(base_location,numbers):

    first_level = []
    for number in numbers:
        first_level += [number//100]

    first_level_set = list(sorted(set(first_level)))

    for i in first_level_set:

        os.mkdir(base_location+'/'+str(i))

        for j, number in enumerate(numbers):

            if first_level[j] == i:
                os.mkdir(base_location+'/'+str(i)+'/'+str(number))

    return

#general.py
#Function to convert a list of numbers to a list of n-digit strings.
def number_to_string(number,string_length):

    number_str = str(number)
    if len(number_str)<=string_length:
        string = '0'*(string_length-len(number_str))+number_str
    else:
        exit('The file number is too great to construct a unique MOCKID (more than 3 digits).')

    return string

#import.py
#Function to extract RA values from a colore or picca format hdulist.
def get_RA(h,input_format):

    if input_format == 'physical_colore':
        RA = h[1].data['RA']
    elif input_format == 'gaussian_colore':
        RA = h[1].data['RA']
    elif input_format == 'picca':
        RA = h[3].data['RA']
    else:
        print('Error.')

    return RA

#import.py
#Function to extract DEC values from a colore or picca format hdulist.
def get_DEC(h,input_format):

    if input_format == 'physical_colore':
        DEC = h[1].data['DEC']
    elif input_format == 'gaussian_colore':
        DEC = h[1].data['DEC']
    elif input_format == 'picca':
        DEC = h[3].data['DEC']
    else:
        print('Error.')

    return DEC

#import.py
#Function to extract Z_QSO values from a colore or picca format hdulist.
def get_Z_QSO(h,input_format):

    if input_format == 'physical_colore':
        Z_QSO = h[1].data['Z_COSMO']
    elif input_format == 'gaussian_colore':
        Z_QSO = h[1].data['Z_COSMO']
    elif input_format == 'picca':
        Z_QSO = h[3].data['Z']
    else:
        print('Error.')

    return Z_QSO

#import.py
#Function to extract DZ_RSD values from a colore.
def get_DZ_RSD(h,input_format):

    if input_format == 'physical_colore':
        DZ_RSD = h[1].data['DZ_RSD']
    elif input_format == 'gaussian_colore':
        DZ_RSD = h[1].data['DZ_RSD']
    elif input_format == 'picca':
        print('Error: DZ_RSD not stored in picca files.')
    else:
        print('Error.')

    return DZ_RSD

#import.py
#Function to extract MOCKID values from a colore, picca or ID format hdulist.
def get_MOCKID(h,input_format,file_number):

    if input_format == 'physical_colore':
        #CoLoRe files do not have a MOCKID entry normally.
        #I am adding entries to any files processed via this code.
        #Hence we try to look for a MOCKID entry, and if this fails, we make one.
        try:
            MOCKID = h[1].data['MOCKID']
        except KeyError:
            h_N_qso = h[1].data.shape[0]
            row_numbers = list(range(h_N_qso))
            MOCKID = make_MOCKID(file_number,row_numbers)
    elif input_format == 'gaussian_colore':
        try:
            MOCKID = h[1].data['MOCKID']
        except KeyError:
            h_N_qso = h[1].data.shape[0]
            row_numbers = list(range(h_N_qso))
            MOCKID = make_MOCKID(file_number,row_numbers)
    elif input_format == 'picca':
        MOCKID = h[3].data['THING_ID']
    elif input_format == 'ID':
        MOCKID = h[1].data['MOCKID']

    return MOCKID

#general.py
#Function to construct an array of MOCKIDs given a file_number and a list of row_numbers.
def make_MOCKID(file_number,row_numbers):

    N_qso = len(row_numbers)
    node = '0'*(len(str(file_number))-5) + str(file_number)

    MOCKID = ['']*N_qso
    for i in range(N_qso):
        row_numbers[i] = str(row_numbers[i]+1)
        if len(row_numbers[i])<=7:
            row_numbers[i] = '0'*(7-len(row_numbers[i]))+row_numbers[i]
        else:
            exit('The row number is too great to construct a unique MOCKID (more than 7 digits).')
        MOCKID[i] = int(node+row_numbers[i])

    MOCKID = np.array(MOCKID)

    return MOCKID

#import.py
#Function to extract Z values from a colore or picca format hdulist.
def get_COSMO(h,input_format):

    lya = 1215.67

    if input_format == 'physical_colore':
        R = h[4].data['R']
        Z = h[4].data['Z']
        D = h[4].data['D']
        V = h[4].data['V']
    elif input_format == 'gaussian_colore':
        R = h[4].data['R']
        Z = h[4].data['Z']
        D = h[4].data['D']
        V = h[4].data['V']
    elif input_format == 'picca':
        LOGLAM_MAP = h[2].data
        Z = ((10**LOGLAM_MAP)/lya) - 1

        # TODO: Update this
        R = np.zeros(Z.shape)
        D = np.zeros(Z.shape)
        V = np.zeros(Z.shape)
    else:
        print('Error.')

    return R, Z, D, V

#import.py
#Function to extract Z values from a colore or picca format hdulist.
def get_lya_lambdas(h,input_format):

    lya = 1215.67

    if input_format == 'physical_colore':
        Z = h[4].data['Z']
        lya_lambdas = lya*(1+Z)
    elif input_format == 'gaussian_colore':
        Z = h[4].data['Z']
        lya_lambdas = lya*(1+Z)
    elif input_format == 'picca':
        LOGLAM_MAP = h[2].data
        lya_lambdas = (10**LOGLAM_MAP)
    else:
        print('Error.')

    return lya_lambdas

#general.py
#Function to determine in which HEALPix pixel each of a set of (RA,DEC) coordinates lies, given N_side.
def make_pixel_ID(N_side,RA,DEC):

    N_qso = RA.shape[0]

    #Convert DEC and RA in degrees to theta and phi in radians.
    theta = (np.pi/180.0)*(90.0-DEC)
    phi = (np.pi/180.0)*RA

    #Make a list of  the HEALPix pixel coordinate of each quasar.
    pixel_ID = ['']*N_qso
    for i in range(N_qso):
        #Check that the angular coordinates are valid. Put all objects with invalid coordinates into a non-realistic ID number (-1).
        if 0 <= theta[i] <= np.pi and 0 <= phi[i] <= 2*np.pi:
            pixel_ID[i] = int(hp.pixelfunc.ang2pix(N_side,theta[i],phi[i],nest=True))
        else:
            pixel_ID[i] = -1

    return pixel_ID

#master.py
#Function to extract data suitable for making ID files from a set of colore or picca format files.
def get_ID_data(original_file_location,original_filename_structure,file_number,input_format,N_side,minimum_z=0.0):

    ID_data = []
    cosmology = []
    N_pixels = 12*N_side**2

    #Open the file and extract the angular coordinate data.
    filename = original_file_location + '/' + original_filename_structure.format(file_number)
    h = fits.open(filename)

    #Extract the component parts of the master file's data from h.
    RA = get_RA(h,input_format)
    DEC = get_DEC(h,input_format)
    Z_QSO_NO_RSD = get_Z_QSO(h,input_format)
    DZ_RSD = get_DZ_RSD(h,input_format)
    MOCKID = get_MOCKID(h,input_format,file_number)
    h_R, h_Z, h_D, h_V = get_COSMO(h,input_format)

    h.close()

    #Construct the remaining component parts of the master file's data.
    pixel_ID = make_pixel_ID(N_side,RA,DEC)
    file_numbers = file_number * np.ones(RA.shape)

    #Calculate Z_QSO_RSD.
    Z_QSO_RSD = Z_QSO_NO_RSD + DZ_RSD

    #Join the pieces of the ID_data together.
    ID_data = list(zip(RA,DEC,Z_QSO_NO_RSD,Z_QSO_RSD,MOCKID,pixel_ID,file_numbers))

    #Sort the MOCKIDs and pixel_IDs into the right order: first by pixel number, and then by MOCKID.
    #Also filter out the objects with Z_QSO<minimum_z
    dtype = [('RA', 'd'), ('DEC', 'd'), ('Z_QSO_NO_RSD', 'd'), ('Z_QSO_RSD', 'd'), ('MOCKID', int), ('PIXNUM', int), ('FILENUM', int)]
    ID = np.array(ID_data, dtype=dtype)
    ID = ID[ID['Z_QSO_NO_RSD']>minimum_z]
    ID_sort = np.sort(ID, order=['PIXNUM','MOCKID'])

    #Make file-pixel map element and MOCKID lookup.
    pixel_ID_set = list(sorted(set([pixel for pixel in ID_sort['PIXNUM'] if pixel>=0])))
    file_pixel_map_element = np.zeros(N_pixels)
    MOCKID_lookup_element = {}
    for pixel in pixel_ID_set:
        file_pixel_map_element[pixel] = 1
        MOCKID_pixel_list = [ID_sort['MOCKID'][i] for i in range(len(ID_sort['PIXNUM'])) if ID_sort['PIXNUM'][i]==pixel]
        MOCKID_lookup_element = {**MOCKID_lookup_element,**{(file_number,pixel):MOCKID_pixel_list}}

    #Construct the cosmology array.
    cosmology_data = list(zip(h_R,h_Z,h_D,h_V))
    dtype = [('R', 'd'), ('Z', 'd'), ('D', 'd'), ('V', 'd')]
    cosmology = np.array(cosmology_data,dtype=dtype)

    return file_number, ID_sort, cosmology, file_pixel_map_element, MOCKID_lookup_element

#master.py
#Function to join together the outputs from 'get_ID_data' in several multiprocessing processes.
def join_ID_data(results,N_side):

    file_numbers = []
    master_results = []
    bad_coordinates_results = []
    cosmology_results = []
    file_pixel_map_results = []
    MOCKID_lookup = {}

    for result in results:
        file_numbers += [result[0]]
        ID_result = result[1]
        master_results += [ID_result[ID_result['PIXNUM']>=0]]
        bad_coordinates_results += [ID_result[ID_result['PIXNUM']<0]]
        # TODO: Something to check that all cosmology results are the same
        cosmology_results = [result[2]]
        file_pixel_map_results += [result[3]]
        MOCKID_lookup = {**MOCKID_lookup,**result[4]}

    file_pixel_map = np.zeros((max(file_numbers)+1,12*(N_side**2)))
    for i, file_number in enumerate(file_numbers):
        file_pixel_map[file_number,:] = file_pixel_map_results[i]
    #print(master_results)
    master_data = np.concatenate(master_results)
    bad_coordinates_data = np.concatenate(bad_coordinates_results)
    cosmology_data = np.concatenate(cosmology_results)
    file_pixel_map = np.vstack(file_pixel_map_results)

    return master_data, bad_coordinates_data, cosmology_data, file_pixel_map, MOCKID_lookup

#master.py
#Function to write a single ID file, given the data.
def write_ID(filename,ID_data,cosmology_data,N_side):

    #Make an appropriate header.
    header = fits.Header()
    header['NSIDE'] = N_side

    #Make the data into tables.
    hdu_ID = fits.BinTableHDU.from_columns(ID_data,header=header,name='CATALOG')
    hdu_cosmology = fits.BinTableHDU.from_columns(cosmology_data,header=header,name='COSMO')

    #Make a primary HDU.
    prihdr = fits.Header()
    prihdu = fits.PrimaryHDU(header=prihdr)

    #Make the .fits file.
    hdulist = fits.HDUList([prihdu,hdu_ID,hdu_cosmology])
    hdulist.writeto(filename)
    hdulist.close()

    return

#master.py
#Function to make the drq files needed for picca xcf functions.
def write_DRQ(filename,RSD_option,ID_data,N_side):

    #Extract data from the ID_data
    RA = ID_data['RA']
    DEC = ID_data['DEC']
    Z = ID_data['Z_QSO'+'_'+RSD_option]
    THING_ID = ID_data['MOCKID']
    PIXNUM = ID_data['PIXNUM']
    N_qso = RA.shape[0]

    #Fill in the data that is not specified.
    MJD = np.zeros(N_qso)
    FID = np.zeros(N_qso)
    PLATE = THING_ID

    #Make the data array.
    dtype = [('RA','f8'),('DEC','f8'),('Z','f8'),('THING_ID',int),('MJD','f8'),('FIBERID',int),('PLATE',int),('PIXNUM',int)]
    DRQ_data = np.array(list(zip(RA,DEC,Z,THING_ID,MJD,FID,PLATE,PIXNUM)),dtype=dtype)

    #Make an appropriate header.
    header = fits.Header()
    header['NSIDE'] = N_side

    #Create a new master file, with the same filename concatenated with '_picca_' and the RSD option chosen.
    prihdr = fits.Header()
    prihdu = fits.PrimaryHDU(header=prihdr)
    hdu_DRQ = fits.BinTableHDU.from_columns(DRQ_data,header=header)

    hdulist = fits.HDUList([prihdu,hdu_DRQ])
    hdulist.writeto(filename)
    hdulist.close()

    return

#physical.py
#From lya_mock_p1d.py
def get_tau(z,density_rows,alpha,beta):
    """transform lognormal density to optical depth, at each z"""
    # add redshift evolution to mean optical depth
    N_cells = density_rows.shape[1]
    TAU_rows = np.zeros(density_rows.shape)
    for j in range(N_cells):
        TAU_rows[:,j] = alpha[j]*(density_rows[:,j]**beta)

    return TAU_rows

#general.py
#Function to make ivar mask
def make_IVAR_rows(IVAR_cutoff,Z_QSO,LOGLAM_MAP):

    N_cells = LOGLAM_MAP.shape[0]
    N_qso = Z_QSO.shape[0]

    lya_lambdas = IVAR_cutoff*(1+Z_QSO)
    IVAR_rows = np.ones((N_qso,N_cells),dtype='float32')
    lambdas = 10**LOGLAM_MAP

    for i in range(N_qso):
        last_relevant_cell = np.searchsorted(lambdas,lya_lambdas[i]) - 1

        for j in range(last_relevant_cell+1,N_cells):
            IVAR_rows[i,j] = 0.

    return IVAR_rows

#physical.py
#Function to convert tau skewers (in rows) to density skewers (in rows).
def tau_to_density(TAU_rows,alpha,beta):

    DENSITY_rows = np.zeros(TAU_rows.shape)
    N_cells = TAU_rows.shape[1]

    for j in range(N_cells):
        DENSITY_rows[:,j] = (TAU_rows[:,j]/alpha[j])**(1/beta)

    return DENSITY_rows

#physical.py
#Function to convert lognormal delta skewers (in rows) to gaussian field skewers (in rows).
def lognormal_delta_to_gaussian(LN_DENSITY_DELTA_rows,SIGMA_G,D):

    LN_DENSITY_rows = 1.0 + LN_DENSITY_DELTA_rows

    GAUSSIAN_DELTA_rows = np.zeros(LN_DENSITY_DELTA_rows.shape)

    if np.array(D).shape[0] == 1:
        D = np.ones(LN_DENSITY_rows.shape[1])*D

    if np.array(SIGMA_G).shape[0] == 1:
        SIGMA_G = np.ones(LN_DENSITY_rows.shape[1])*SIGMA_G

    for j in range(GAUSSIAN_DELTA_rows.shape[1]):
        GAUSSIAN_DELTA_rows[:,j] = (np.log(LN_DENSITY_rows[:,j]))/D[j] + (D[j])*(SIGMA_G[j]**2)/2

    GAUSSIAN_DELTA_rows = GAUSSIAN_DELTA_rows.astype('float32')

    return GAUSSIAN_DELTA_rows

#physical.py
#Function to convert gaussian field skewers (in rows) to lognormal delta skewers (in rows).
def gaussian_to_lognormal_delta(GAUSSIAN_DELTA_rows,SIGMA_G,D):

    LN_DENSITY_rows = np.zeros(GAUSSIAN_DELTA_rows.shape)
    LN_DENSITY_DELTA_rows = np.zeros(GAUSSIAN_DELTA_rows.shape)

    SIGMA_G = SIGMA_G*np.ones(GAUSSIAN_DELTA_rows.shape[1])

    D = D*np.ones(GAUSSIAN_DELTA_rows.shape[1])

    for j in range(GAUSSIAN_DELTA_rows.shape[1]):
        LN_DENSITY_rows[:,j] = np.exp(D[j]*GAUSSIAN_DELTA_rows[:,j] - ((D[j])**2)*(SIGMA_G[j]**2)/2.)

    LN_DENSITY_DELTA_rows = LN_DENSITY_rows - 1

    LN_DENSITY_DELTA_rows = LN_DENSITY_DELTA_rows.astype('float32')

    return LN_DENSITY_DELTA_rows

#physical.py
#Function to convert from density to tau using alpha*density^beta
def density_to_tau(density,alpha,beta):

    tau = alpha*(density**beta)

    return tau

#physical.py
#Function to convert from density to flux using e^-(alpha*density^beta)
def density_to_flux(density,alpha,beta):

    F = np.exp(-alpha*(density**beta))

    return F

#general.py
#Function to determine the first index corresponding to a value in an array greater than a minimum value.
def get_first_relevant_index(minimum,values):

    if minimum > 0:
        first_relevant_index = np.argmax(values >= minimum)
    else:
        first_relevant_index = 0

    return first_relevant_index

#general.py
#Function to determine the indices corresponding to the values in an array greater than a minimum value.
def get_relevant_indices(minimum,values):

    N = values.shape[0]
    relevant_indices = [i for i in range(N) if values[i] > minimum]

    return relevant_indices

#general.py
# TODO: sort out the float/integer problem
#Function to retrieve relevant simulation parameters from the param.cfg file.
def get_simulation_parameters(location,filename):

    #Create a string of the parameter file to search.
    parameter_str = open(location + '/' + filename,'r').read()

    #Define the parameters to search for and the intricacies of the parameter file.
    divider = '\n'
    #parameters = [('dens_type','int'),('r_smooth','f4'),('n_grid','int'),('gaussian_skewers','str'),('omega_M','f4'),('omega_L','f4'),('omega_B','f4'),('h','f4'),('w','f4'),('ns','f4'),('sigma_8','f4')]
    parameters = [('dens_type','int'),('r_smooth','f4'),('n_grid','int'),('omega_M','f4'),('omega_L','f4'),('omega_B','f4'),('h','f4'),('w','f4'),('ns','f4'),('sigma_8','f4')]
    equality_format = ' = '
    N_parameters = len(parameters)

    parameter_values = np.array([tuple([0]*N_parameters)],dtype=parameters)

    #For each parameter defined, find its value and put it into the output array.
    for i, parameter in enumerate(parameters):
        search_term = parameter[0] + equality_format
        data_type = parameter[1]
        N_char = len(search_term)

        first_char = parameter_str.find(search_term)
        parameter_values[0][i] = float(parameter_str[first_char+N_char:parameter_str.find(divider,first_char+N_char)])

    return parameter_values

#general.py
#Function to normalise a set of delta skewer rows to zero mean according to given weights.
#If all weights for a given cell are zero, then the output will be zero in that cell for all skewers.
def normalise_deltas(DELTA_rows,mean_DELTA):

    N_cells = DELTA_rows.shape[1]
    DELTA_rows_normalised = np.zeros(DELTA_rows.shape)

    for j in range(N_cells):
        DELTA_rows_normalised[:,j] = (DELTA_rows[:,j] + 1)/(mean_DELTA[j] + 1) - 1

    return DELTA_rows_normalised

# TODO: write this
class simulation_parameters:
    def __init__():

        return

    @classmethod
    def get_parameters(cls,location,filename):

        return

#stats.py
#Function to calculate the mean of deltas, mean of deltas^2, and N.
def return_means(DELTA_rows,weights,sample_pc=1.0):
    DELTA_SQUARED_rows = DELTA_rows**2
    N_cells = DELTA_rows.shape[1]

    N = np.zeros(N_cells)
    mean_DELTA = np.zeros(N_cells)
    mean_DELTA_SQUARED = np.zeros(N_cells)

    for j in range(N_cells):
        N[j] = np.sum(weights[:,j],axis=0)
        if N[j] > 0:
            mean_DELTA[j] = np.average(DELTA_rows[:,j],weights=weights[:,j])
            mean_DELTA_SQUARED[j] = np.average(DELTA_SQUARED_rows[:,j],weights=weights[:,j])

    return N, mean_DELTA, mean_DELTA_SQUARED

#stats.py
#
def combine_pixel_means(results):

    N_cells = results[0][0].shape[0]
    N = np.zeros(N_cells)
    mean_DELTA = np.zeros(N_cells)
    mean_DELTA_SQUARED = np.zeros(N_cells)

    for result in results:
        N += result[0]

    for j in range(N_cells):
        if N[j] > 0:
            for result in results:
                mean_DELTA[j] += result[0][j]*result[1][j]/N[j]
                mean_DELTA_SQUARED[j] += result[0][j]*result[2][j]/N[j]

    var_DELTA = mean_DELTA_SQUARED - mean_DELTA**2

    return N, mean_DELTA, var_DELTA

#stats.py
#Function to take a list of sets of statistics (as produced by 'get_statistics'), and calculate means and variances.
def combine_means(means_list):

    means_shape = means_list[0].shape
    means_data_type = means_list[0].dtype
    N_cells = means_shape[0]

    quantities = ['GAUSSIAN_DELTA','GAUSSIAN_DELTA_SQUARED','DENSITY_DELTA','DENSITY_DELTA_SQUARED','F','F_SQUARED','F_DELTA','F_DELTA_SQUARED']

    combined_means = np.zeros(means_shape,dtype=means_data_type)
    for means_array in means_list:
        combined_means['N'] += means_array['N']

    for i in range(N_cells):
        if combined_means['N'][i] > 0:
            for quantity in quantities:
                for means_array in means_list:
                    combined_means[quantity][i] += (means_array['N'][i]*means_array[quantity][i])/combined_means['N'][i]

    return combined_means

#stats.py
#Function to convert a set of means of quantities and quantities squared (as outputted by 'combine_means') to a set of means and variances.
def means_to_statistics(means):

    statistics_dtype = [('N', 'f4')
        , ('GAUSSIAN_DELTA_MEAN', 'f4'), ('GAUSSIAN_DELTA_VAR', 'f4')
        , ('DENSITY_DELTA_MEAN', 'f4'), ('DENSITY_DELTA_VAR', 'f4')
        , ('F_MEAN', 'f4'), ('F_VAR', 'f4')
        , ('F_DELTA_MEAN', 'f4'), ('F_DELTA_VAR', 'f4')]

    statistics = np.zeros(means.shape,dtype=statistics_dtype)

    statistics['N'] = means['N']
    statistics['GAUSSIAN_DELTA_MEAN'] = means['GAUSSIAN_DELTA']
    statistics['DENSITY_DELTA_MEAN'] = means['DENSITY_DELTA']
    statistics['F_MEAN'] = means['F']
    statistics['F_DELTA_MEAN'] = means['F_DELTA']

    statistics['GAUSSIAN_DELTA_VAR'] = means['GAUSSIAN_DELTA_SQUARED'] - means['GAUSSIAN_DELTA']**2
    statistics['DENSITY_DELTA_VAR'] = means['DENSITY_DELTA_SQUARED'] - means['DENSITY_DELTA']**2
    statistics['F_VAR'] = means['F_SQUARED'] - means['F']**2
    statistics['F_DELTA_VAR'] = means['F_DELTA_SQUARED'] - means['F_DELTA']**2

    return statistics

#stats.py
#Function to write the statistics data to file, along with an HDU extension contanint cosmology data.
def write_statistics(location,N_side,statistics,cosmology_data):

    #Construct HDU from the statistics array.
    prihdr = fits.Header()
    prihdu = fits.PrimaryHDU(header=prihdr)
    cols_stats = fits.ColDefs(statistics)
    hdu_stats = fits.BinTableHDU.from_columns(cols_stats,name='STATISTICS')
    cols_cosmology = fits.ColDefs(cosmology_data)
    hdu_cosmology = fits.BinTableHDU.from_columns(cols_cosmology,name='COSMO')

    #Put the HDU into an HDUlist and save as a new file. Close the HDUlist.
    filename = '/statistics.fits'
    hdulist = fits.HDUList([prihdu,hdu_stats,hdu_cosmology])
    hdulist.writeto(location+filename)
    hdulist.close

    return

#general.py
#Function to interpolate via the NGP method.
def get_NGPs(x,x_new):

    NGPs = np.zeros(x_new.shape)
    
    for i,x_new_value in enumerate(x_new):
        distances2 = (x-x_new_value)**2
        NGPs[i] = np.argmin(distances2)

    return NGPs

#ssp.py
#Function to generate random Gaussian skewers with a given standard deviation.
def get_gaussian_skewers(generator,N_cells,sigma_G=1.0,N_skewers=1):

    if N_cells*N_skewers == 1:
        size = 1
    else:
        size=(N_skewers,N_cells)

    gaussian_skewers = fast_prng.normal(size=size,scale=sigma_G)

    """
    gaussian_skewers = np.random.normal(size=(N_skewers,N_cells),scale=sigma_G)
    """
    return gaussian_skewers

#ssp.py
#Function to generate random Gaussian fields at a given redshift.
#From lya_mock_functions
def get_gaussian_fields(z,N_cells,dv_kms=10.0,N_skewers=1,new_seed=None,white_noise=True):
    """Generate N_skewers Gaussian fields at redshift z_c.

      If new_seed is set, it will reset random generator with it."""

    random_state = np.random.RandomState(new_seed)

    # number of Fourier modes
    NF = int(N_cells/2+1)

    # get frequencies (wavenumbers in units of s/km)
    k_kms = np.fft.rfftfreq(N_cells)*2*np.pi/dv_kms

    # get power evaluated at each k_kms
    P_kms = power_kms(z,k_kms,dv_kms,white_noise=white_noise)

    # generate random Fourier modes
    modes = np.empty([N_skewers,NF], dtype=complex)
    modes[:].real = np.reshape(random_state.normal(size=N_skewers*NF),[N_skewers,NF])
    modes[:].imag = np.reshape(random_state.normal(size=N_skewers*NF),[N_skewers,NF])

    # normalize to desired power (and enforce real for i=0, i=NF-1)
    modes[:,0] = modes[:,0].real * np.sqrt(P_kms[0])
    modes[:,-1] = modes[:,-1].real * np.sqrt(P_kms[-1])
    modes[:,1:-1] *= np.sqrt(0.5*P_kms[1:-1])

    # inverse FFT to get (normalized) delta field
    delta = np.fft.irfft(modes,n=N_cells) * np.sqrt(N_cells/dv_kms)

    return delta

#ssp.py
#Function to return a gaussian P1D in k.
#From lya_mock_functions
def power_kms(z_c,k_kms,dv_kms,white_noise):
    """Return Gaussian P1D at different wavenumbers k_kms (in s/km), fixed z_c.

      Other arguments:
        dv_kms: if non-zero, will multiply power by top-hat kernel of this width
        white_noise: if set to True, will use constant power of 100 km/s
    """
    if white_noise: return np.ones_like(k_kms)*100.0
    # power used to make mocks in from McDonald et al. (2006)
    A = power_amplitude(z_c)
    k1 = 0.001
    n = 0.7
    R1 = 5.0
    # compute term without smoothing
    P = A * (1.0+pow(0.01/k1,n)) / (1.0+pow(k_kms/k1,n))
    # smooth with Gaussian and top hat
    kdv = np.fmax(k_kms*dv_kms,0.000001)
    P *= np.exp(-pow(k_kms*R1,2)) * pow(np.sin(kdv/2)/(kdv/2),2)
    return P

#ssp.py
#Function to integrate under the 1D power spectrum to return the value of sigma_dF at a given redshift.
def get_sigma_dF_P1D(z,l_hMpc=0.25,Om=0.3):
    #Choose log spaced values of k
    k_hMpc_max = 100.0/l_hMpc
    k_hMpc = np.logspace(-5,np.log10(k_hMpc_max),10**5)

    # TODO: generalise the conversion in here
    # need to go from Mpc/h to km/s, using dv / dX = H(z) / (1+z)
    # we will define H(z) = 100 h E(z)
    # with E(z) = sqrt(Omega_m(1+z)^3 + Omega_L), and assume flat universe
    E_z = np.sqrt(Om*(1+z)**3 + (1-Om))
    dkms_dhMpc = 100. * E_z / (1+z)

    # transform input wavenumbers to s/km
    k_kms = k_hMpc / dkms_dhMpc

    # get power in units of km/s
    pk_kms = P1D_z_kms_PD2013(z,k_kms)

    # transform to h/Mpc
    pk_hMpc = pk_kms / dkms_dhMpc

    # compute Fourier transform of Top-Hat filter of size l_hMpc
    W_hMpc = np.sinc((k_hMpc*l_hMpc)/(2*np.pi))
    sigma_dF = np.sqrt((1/np.pi)*np.trapz((W_hMpc**2)*pk_hMpc,k_hMpc))

    return sigma_dF

#tuning.py
#Function to return the P1D from Palanque-Delabrouille et al. (2013)
#copied from lyaforecast
def P1D_z_kms_PD2013(z,k_kms):
    """Fitting formula for 1D P(z,k) from Palanque-Delabrouille et al. (2013).
        Wavenumbers and power in units of km/s. Corrected to be flat at low-k"""
    # numbers from Palanque-Delabrouille (2013)
    A_F = 0.064
    n_F = -2.55
    alpha_F = -0.1
    B_F = 3.55
    beta_F = -0.28
    k0 = 0.009
    z0 = 3.0
    n_F_z = n_F + beta_F * np.log((1+z)/(1+z0))
    # this function would go to 0 at low k, instead of flat power
    k_min=k0*np.exp((-0.5*n_F_z-1)/alpha_F)
    k_kms = np.fmax(k_kms,k_min)
    exp1 = 3 + n_F_z + alpha_F * np.log(k_kms/k0)
    toret = np.pi * A_F / k0 * pow(k_kms/k0, exp1-1) * pow((1+z)/(1+z0), B_F)
    return toret

#tuning.py
#Function to return the mean value of F at a given redshift.
#Equation from F-R2012, equation 2.11
def get_mean_F_model(z):
    mean_F = np.exp((np.log(0.8))*(((1+z)/3.25)**3.2))
    return mean_F

#stats.py
#Function to calculate mean_F and sigma_dF for given values of sigma_G, alpha and beta.
def get_flux_stats(sigma_G,alpha,beta,D,mean_only=False,int_lim_fac=10.0):

    int_lim = sigma_G*int_lim_fac

    delta_G_integral = np.linspace(-int_lim,int_lim,10**4)
    delta_G_integral = np.reshape(delta_G_integral,(1,delta_G_integral.shape[0]))

    prob_delta_G = (1/((np.sqrt(2*np.pi))*sigma_G))*np.exp(-(delta_G_integral**2)/(2*(sigma_G**2)))

    density_integral = gaussian_to_lognormal_delta(delta_G_integral,sigma_G,D) + 1
    F_integral = density_to_flux(density_integral,alpha,beta)

    mean_F = np.trapz(prob_delta_G*F_integral,delta_G_integral)[0]

    if mean_only == False:
        delta_F_integral = F_integral/mean_F - 1
        integrand = prob_delta_G*(delta_F_integral**2)
        sigma_dF = (np.sqrt(np.trapz(integrand,delta_G_integral)[0]))
    else:
        sigma_dF = None

    return mean_F, sigma_dF

#tuning.py
#Function to find the value of alpha required to match mean_F to a specified value.
def find_alpha(sigma_G,mean_F_required,beta,D,alpha_log_low=-3.0,alpha_log_high=10.0,tolerance=0.0001,max_iter=30):
    #print('---> mean_F required={:2.2f}'.format(mean_F_required))
    count = 0
    exit = 0
    while exit == 0 and count < max_iter:
        alpha_log_midpoint = (alpha_log_low + alpha_log_high)/2.0

        mean_F_al,sigma_dF_al = get_flux_stats(sigma_G,10**alpha_log_low,beta,D,mean_only=True)
        mean_F_am,sigma_dF_am = get_flux_stats(sigma_G,10**alpha_log_midpoint,beta,D,mean_only=True)
        mean_F_ah,sigma_dF_ah = get_flux_stats(sigma_G,10**alpha_log_high,beta,D,mean_only=True)

        #print('---> alphas=({:2.2f},{:2.2f},{:2.2f}) gives mean_F=({:2.2f},{:2.2f},{:2.2f})'.format(10**alpha_log_low,10**alpha_log_midpoint,10**alpha_log_high,mean_F_al,mean_F_am,mean_F_ah))

        if np.sign(mean_F_al-mean_F_required) * np.sign(mean_F_am-mean_F_required) > 0:
            alpha_log_low = alpha_log_midpoint
        else:
            alpha_log_high = alpha_log_midpoint

        if abs(mean_F_am/mean_F_required - 1) < tolerance:
            exit = 1
        else:
            count += 1

    if exit == 0:
        # TODO: something other than print here. Maybe make a log of some kind?
        print('\nvalue of mean_F did not converge to within tolerance: error is {:3.2%}'.format(mean_F_am/mean_F_required - 1))

    alpha = 10**alpha_log_midpoint
    mean_F,sigma_dF = get_flux_stats(sigma_G,alpha,beta,D)

    return alpha,mean_F,sigma_dF

#tuning.py
#Function to find the values of alpha and sigma_G required to match mean_F and sigma_dF to specified values.
def find_sigma_G(mean_F_required,sigma_dF_required,beta,D,sigma_G_start=0.001,step_size=1.0,tolerance=0.001,max_steps=30):
    #print('sigma_dF required={:2.2f}'.format(sigma_dF_required))
    #print(' ')
    #print(' ')
    count = 0
    exit = 0
    sigma_G = sigma_G_start

    while exit == 0 and count < max_steps:

        alpha,mean_F,sigma_dF = find_alpha(sigma_G,mean_F_required,beta,D)

        if abs(sigma_dF/sigma_dF_required - 1) < tolerance:
            exit = 1
            #print('sigma_G={:2.4f} gives sigma_dF={:2.4f}. Satisfied. Exiting...'.format(sigma_G,sigma_dF))
        elif sigma_dF < sigma_dF_required:
            #print('sigma_G={:2.4f} gives sigma_dF={:2.4f}. Too low. Stepping forwards...'.format(sigma_G,sigma_dF))
            sigma_G += step_size
            count += 1
        elif sigma_dF > sigma_dF_required:
            #print('sigma_G={:2.4f} gives sigma_dF={:2.4f}. Too high. Stepping backwards...'.format(sigma_G,sigma_dF))
            sigma_G_too_high = sigma_G
            sigma_G -= step_size
            step_size = step_size/10.0
            sigma_G += step_size
            count += 1

        #print('error: ',(sigma_dF/sigma_dF_required - 1))

        """
        sigma_G_log_low = -3.0
        sigma_G_log_high = 1.0

        sigma_G_log_midpoint = (sigma_G_log_low + sigma_G_log_high)/2.0

        alpha_sGl,mean_F_sGl,sigma_dF_sGl = find_alpha(10**sigma_G_log_low,mean_F_required,beta,D)
        alpha_sGm,mean_F_sGm,sigma_dF_sGm = find_alpha(10**sigma_G_log_midpoint,mean_F_required,beta,D)
        alpha_sGh,mean_F_sGh,sigma_dF_sGh = find_alpha(10**sigma_G_log_high,mean_F_required,beta,D)

        print('sigma_Gs=({:2.2f},{:2.2f},{:2.2f}) gives sigma_dFs=({:2.2f},{:2.2f},{:2.2f})'.format(10**sigma_G_log_low,10**sigma_G_log_midpoint,10**sigma_G_log_high,sigma_dF_sGl,sigma_dF_sGm,sigma_dF_sGh))

        if np.sign(sigma_dF_sGl-sigma_dF_required) * np.sign(sigma_dF_sGm-sigma_dF_required) > 0:
            sigma_G_log_low = sigma_G_log_midpoint
        else:
            sigma_G_log_high = sigma_G_log_midpoint

        if abs(sigma_dF_sGm/sigma_dF_required - 1) < tolerance:
            exit = 1
        else:
            count += 1
        """

    #print('Testing finished. Final values are:')
    #print('sigma_G={:2.4f} gives sigma_dF={:2.4f}.'.format(sigma_G,sigma_dF))
    #print('error: ',(sigma_dF/sigma_dF_required - 1))

    if exit == 0:
        # TODO: something other than print here. Maybe make a log of some kind?
        print('\nvalue of sigma_dF did not converge to within tolerance: error is {:3.2%}'.format(sigma_dF/sigma_dF_required - 1))
        sigma_G = (sigma_G+sigma_G_too_high)/2.0
        alpha,mean_F,sigma_dF = find_alpha(sigma_G,mean_F_required,beta,D)

    #print('Final check finished. Final values are:')
    #print('sigma_G={:2.4f} gives sigma_dF={:2.4f}.'.format(sigma_G,sigma_dF))
    #print('error: ',(sigma_dF/sigma_dF_required - 1))
    #print(' ')
    """
    alpha = alpha_sGm
    sigma_G = 10**sigma_G_log_midpoint
    mean_F = mean_F_sGm
    sigma_dF = sigma_dF_sGm
    """
    return alpha,sigma_G,mean_F,sigma_dF

#data.py
#Definition of a generic 'simulation_data' class, from which it is easy to save in new formats.
class simulation_data:
    #Initialisation function.
    def __init__(self,N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A):

        self.N_qso = N_qso
        self.N_cells = N_cells
        self.SIGMA_G = SIGMA_G
        self.ALPHA = ALPHA

        self.TYPE = TYPE
        self.RA = RA
        self.DEC = DEC
        self.Z_QSO = Z_QSO
        self.DZ_RSD = DZ_RSD
        self.MOCKID = MOCKID
        self.PLATE = PLATE
        self.MJD = MJD
        self.FIBER = FIBER

        self.GAUSSIAN_DELTA_rows = GAUSSIAN_DELTA_rows
        self.DENSITY_DELTA_rows = DENSITY_DELTA_rows
        self.VEL_rows = VEL_rows
        self.IVAR_rows = IVAR_rows
        self.F_rows = F_rows

        self.R = R
        self.Z = Z
        self.D = D
        self.V = V
        self.LOGLAM_MAP = LOGLAM_MAP
        self.A = A

        self.linear_skewer_RSDs_added = False
        self.thermal_skewer_RSDs_added = False

        self.density_computed = False
        self.tau_computed = False
        self.flux_computed = False

        return

    #Method to extract reduced data from an input file of a given format, with a given list of MOCKIDs.
    @classmethod
    def get_gaussian_skewers_object(cls,filename,file_number,input_format,MOCKIDs=None,lambda_min=0,IVAR_cutoff=lya,SIGMA_G=None):

        lya = 1215.67

        h = fits.open(filename)

        h_MOCKID = get_MOCKID(h,input_format,file_number)
        h_R, h_Z, h_D, h_V = get_COSMO(h,input_format)
        h_lya_lambdas = get_lya_lambdas(h,input_format)

        if MOCKIDs != None:
            #Work out which rows in the hdulist we are interested in.
            rows = ['']*len(MOCKIDs)
            s = set(MOCKIDs)
            j = 0
            for i, qso in enumerate(h_MOCKID):
                if qso in s:
                    rows[j] = i
                    j = j+1
        else:
            rows = list(range(h_MOCKID.shape[0]))

        #Calculate the first_relevant_cell.
        first_relevant_cell = np.searchsorted(h_lya_lambdas,lambda_min)
        actual_lambda_min = h_lya_lambdas[first_relevant_cell]

        if input_format == 'physical_colore':

            #Extract data from the HDUlist.
            TYPE = h[1].data['TYPE'][rows]
            RA = h[1].data['RA'][rows]
            DEC = h[1].data['DEC'][rows]
            Z_QSO = h[1].data['Z_COSMO'][rows]
            DZ_RSD = h[1].data['DZ_RSD'][rows]

            DENSITY_DELTA_rows = h[2].data[rows,first_relevant_cell:]

            VEL_rows = h[3].data[rows,first_relevant_cell:]

            Z = h[4].data['Z'][first_relevant_cell:]
            R = h[4].data['R'][first_relevant_cell:]
            D = h[4].data['D'][first_relevant_cell:]
            V = h[4].data['V'][first_relevant_cell:]

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = Z.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive the MOCKID and LOGLAM_MAP.
            MOCKID = get_MOCKID(h,input_format,file_number)
            LOGLAM_MAP = np.log10(lya*(1+Z))

            #Calculate the Gaussian skewers.
            GAUSSIAN_DELTA_rows = lognormal_delta_to_gaussian(DENSITY_DELTA_rows,SIGMA_G,D)

            #Set the remaining variables to None
            DENSITY_DELTA_rows = None
            A = None
            ALPHA = None
            F_rows = None

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)

            IVAR_rows = make_IVAR_rows(IVAR_cutoff,Z_QSO,LOGLAM_MAP)

        elif input_format == 'gaussian_colore':

            #Extract data from the HDUlist.
            TYPE = h[1].data['TYPE'][rows]
            RA = h[1].data['RA'][rows]
            DEC = h[1].data['DEC'][rows]
            Z_QSO = h[1].data['Z_COSMO'][rows]
            DZ_RSD = h[1].data['DZ_RSD'][rows]

            GAUSSIAN_DELTA_rows = h[2].data[rows,first_relevant_cell:]

            VEL_rows = h[3].data[rows,first_relevant_cell:]

            Z = h[4].data['Z'][first_relevant_cell:]
            R = h[4].data['R'][first_relevant_cell:]
            D = h[4].data['D'][first_relevant_cell:]
            V = h[4].data['V'][first_relevant_cell:]

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = Z.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive the MOCKID and LOGLAM_MAP.
            if MOCKIDs != None:
                MOCKID = MOCKIDs
            else:
                MOCKID = get_MOCKID(h,input_format,file_number)
            LOGLAM_MAP = np.log10(lya*(1+Z))

            #Set the remaining variables to None
            DENSITY_DELTA_rows = None
            A = None
            ALPHA = None
            F_rows = None

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)

            IVAR_rows = make_IVAR_rows(IVAR_cutoff,Z_QSO,LOGLAM_MAP)

        elif input_format == 'picca_density':

            #Extract data from the HDUlist.
            DENSITY_DELTA_rows = h[0].data.T[rows,first_relevant_cell:]

            IVAR_rows = h[1].data.T[rows,first_relevant_cell:]

            LOGLAM_MAP = h[2].data[first_relevant_cell:]

            RA = h[3].data['RA'][rows]
            DEC = h[3].data['DEC'][rows]
            Z_QSO = h[3].data['Z'][rows]
            PLATE = h[3].data['PLATE'][rows]
            MJD = h[3].data['MJD'][rows]
            FIBER = h[3].data['FIBER'][rows]
            MOCKID = h[3].data['THING_ID'][rows]

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = LOGLAM_MAP.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive Z and transmitted flux fraction.
            Z = (10**LOGLAM_MAP)/lya - 1

            #Calculate the Gaussian skewers.
            GAUSSIAN_DELTA_rows = lognormal_delta_to_gaussian(DENSITY_DELTA_rows,SIGMA_G,D)

            #Set the remaining variables to None
            DENSITY_DELTA_rows = None
            A = None
            ALPHA = None
            F_rows = None

            """
            Can we calculate DZ_RSD,R,D,V?
            """

            #Insert placeholder variables for remaining variables.
            TYPE = np.zeros(RA.shape[0])
            R = np.zeros(Z.shape[0])
            D = np.zeros(Z.shape[0])
            V = np.zeros(Z.shape[0])
            DZ_RSD = np.zeros(RA.shape[0])
            VEL_rows = np.zeros(DENSITY_DELTA_rows.shape)

        else:
            print('Input format not recognised: current options are "colore" and "picca".')
            print('Please choose one of these options and try again.')

        h.close()

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Function to trim skewers according to a minimum value of lambda. QSOs with no relevant cells are removed.
    def trim_skewers(self,lambda_min,min_catalog_z,extra_cells=0):

        lambdas = 10**(self.LOGLAM_MAP)
        first_relevant_cell = np.searchsorted(lambdas,lambda_min)

        #Determine which QSOs have any relevant cells to keep.
        """
        relevant_QSOs = []
        for i in range(self.N_qso):
            lambda_QSO = lya*(1 + self.Z_QSO[i])
            if self.IVAR_rows[i,first_relevant_cell] > 0:
                relevant_QSOs += [i]
        """
        relevant_QSOs = self.Z_QSO>min_catalog_z

        #If we want to keep any extra_cells, we subtract from the first_relevant_cell.
        first_relevant_cell -= extra_cells

        #Remove QSOs no longer needed.
        self.N_qso = len(relevant_QSOs)

        self.TYPE = self.TYPE[relevant_QSOs]
        self.RA = self.RA[relevant_QSOs]
        self.DEC = self.DEC[relevant_QSOs]
        self.Z_QSO = self.Z_QSO[relevant_QSOs]
        self.DZ_RSD = self.DZ_RSD[relevant_QSOs]
        self.MOCKID = self.MOCKID[relevant_QSOs]
        self.PLATE = self.PLATE[relevant_QSOs]
        self.MJD = self.MJD[relevant_QSOs]
        self.FIBER = self.FIBER[relevant_QSOs]

        self.GAUSSIAN_DELTA_rows = self.GAUSSIAN_DELTA_rows[relevant_QSOs,:]
        if self.density_computed == True:
            self.DENSITY_DELTA_rows = self.DENSITY_DELTA_rows[relevant_QSOs,:]
        self.VEL_rows = self.VEL_rows[relevant_QSOs,:]
        self.IVAR_rows = self.IVAR_rows[relevant_QSOs,:]
        if self.tau_computed == True:
            self.TAU_rows = self.TAU_rows[relevant_QSOs,:]
        if self.flux_computed == True:
            self.F_rows = self.F_rows[relevant_QSOs,:]

        #Now trim the skewers of the remaining QSOs.
        self.N_cells -= first_relevant_cell

        self.GAUSSIAN_DELTA_rows = self.GAUSSIAN_DELTA_rows[:,first_relevant_cell:]
        if self.density_computed == True:
            self.DENSITY_DELTA_rows = self.DENSITY_DELTA_rows[:,first_relevant_cell:]
        self.VEL_rows = self.VEL_rows[:,first_relevant_cell:]
        self.IVAR_rows = self.IVAR_rows[:,first_relevant_cell:]
        if self.tau_computed == True:
            self.TAU_rows = self.TAU_rows[:,first_relevant_cell:]
        if self.flux_computed == True:
            self.F_rows = self.F_rows[:,first_relevant_cell:]

        self.R = self.R[first_relevant_cell:]
        self.Z = self.Z[first_relevant_cell:]
        self.D = self.D[first_relevant_cell:]
        self.V = self.V[first_relevant_cell:]
        self.LOGLAM_MAP = self.LOGLAM_MAP[first_relevant_cell:]

        return

    #Function to add small scale gaussian fluctuations.
    def add_small_scale_gaussian_fluctuations(self,cell_size,sigma_G_z_values,extra_sigma_G_values,generator,amplitude=1.0,white_noise=False,lambda_min=0.0,IVAR_cutoff=lya):

        # TODO: Is NGP really the way to go?

        #Add small scale fluctuations
        old_R = self.R
        Rmax = np.max(old_R)
        Rmin = np.min(old_R)
        new_R = np.arange(Rmin,Rmax,cell_size)
        new_N_cells = new_R.shape[0]

        NGPs = get_NGPs(old_R,new_R).astype(int)
        expanded_GAUSSIAN_DELTA_rows = np.zeros((self.N_qso,new_N_cells))

        for i in range(self.N_qso):
            expanded_GAUSSIAN_DELTA_rows[i,:] = self.GAUSSIAN_DELTA_rows[i,NGPs]

        #Redefine the necessary variables (N_cells, Z, D etc)
        self.N_cells = new_N_cells
        self.R = new_R

        # TODO: Ideally would want to recompute these rather than interpolating?
        self.Z = np.interp(new_R,old_R,self.Z)
        self.D = np.interp(new_R,old_R,self.D)
        self.V = np.interp(new_R,old_R,self.V)
        self.LOGLAM_MAP = np.log10(lya*(1+self.Z))

        # TODO: What to do with this?
        self.VEL_rows = self.VEL_rows[:,NGPs]

        #Make new IVAR rows.
        self.IVAR_rows = make_IVAR_rows(IVAR_cutoff,self.Z_QSO,self.LOGLAM_MAP)

        #For each skewer, determine the last relevant cell
        first_relevant_cells = np.zeros(self.N_qso)
        last_relevant_cells = np.zeros(self.N_qso)
        for i in range(self.N_qso):
            first_relevant_cell = np.searchsorted(10**(self.LOGLAM_MAP),lambda_min)
            if self.linear_skewer_RSDs_added == True:
                last_relevant_cell = np.searchsorted(self.Z,self.Z_QSO[i]+self.DZ_RSD[i]) - 1
            else:
                last_relevant_cell = np.searchsorted(self.Z,self.Z_QSO[i]) - 1

            #Clip the gaussian skewers so that they are zero after the quasar.
            #This avoids effects from NGP interpolation).
            expanded_GAUSSIAN_DELTA_rows[i,last_relevant_cell + 1:] = 0

            first_relevant_cells[i] = first_relevant_cell
            last_relevant_cells[i] = last_relevant_cell

        """
        # TODO: Improve this
        #1 by 1? Or just N_skewers=N_qso?
        extra_variance = get_gaussian_fields(z,self.N_cells,sigma_G=extra_sigma_G,dv_kms=10.0,N_skewers=self.N_qso,white_noise=white_noise)
        final_GAUSSIAN_DELTA_rows = expanded_GAUSSIAN_DELTA_rows + amplitude*extra_variance
        """

        extra_sigma_G = np.interp(self.Z,sigma_G_z_values,extra_sigma_G_values)

        extra_var = np.zeros(expanded_GAUSSIAN_DELTA_rows.shape)

        for j in range(self.N_cells):
            relevant_QSOs = [i for i in range(self.N_qso) if first_relevant_cells[i]<=j and last_relevant_cells[i]>=j]
            extra_var[relevant_QSOs,j] = generator.normal(scale=extra_sigma_G[j],size=len(relevant_QSOs))

        expanded_GAUSSIAN_DELTA_rows += amplitude*extra_var
        """
        for i in range(self.N_qso):
            first_relevant_cell = first_relevant_cells[i].astype('int32')
            last_relevant_cell = last_relevant_cells[i].astype('int32')

            #Number of cells needed is either the dist between the first and last relevant cells, or 0
            N_cells_needed = np.max([(last_relevant_cell - first_relevant_cell).astype('int32'),0])

            extra_var = np.zeros(N_cells_needed)


            #Pass the generator to get_gaussian_skewers, along with the required sigma, and the size, and the seed
            seed = self.MOCKID[i]
            extra_var = get_gaussian_skewers(generator,N_cells_needed,extra_sigma_G[first_relevant_cell:last_relevant_cell],new_seed=seed)
            #Generate a skewer of the right size with the given seed into 'extra_var'
            #Add on extra var *amplitude


            for j in range(first_relevant_cell,last_relevant_cell):
                extra_sigma_G_cell = extra_sigma_G[j]
                extra_var[j-first_relevant_cell] = get_gaussian_skewers(1,extra_sigma_G_cell)

            if last_relevant_cell >= 0:

                expanded_GAUSSIAN_DELTA_rows[i,first_relevant_cell:last_relevant_cell] += amplitude*extra_var
            """
        self.GAUSSIAN_DELTA_rows = expanded_GAUSSIAN_DELTA_rows
        self.SIGMA_G = np.sqrt(extra_sigma_G**2 + (self.SIGMA_G)**2)

        dtype = [('R', 'f8'), ('Z', 'f8'), ('D', 'f8'), ('V', 'f8')]
        new_cosmology = np.array(list(zip(self.R,self.Z,self.D,self.V)),dtype=dtype)

        return new_cosmology

    #Function to add physical skewers to the object via a lognormal transformation.
    def compute_physical_skewers(self,density_type='lognormal'):

        self.DENSITY_DELTA_rows = gaussian_to_lognormal_delta(self.GAUSSIAN_DELTA_rows,self.SIGMA_G,self.D)
        self.density_computed = True

        return

    #Function to add physical skewers to the object via a lognormal transformation.
    def compute_tau_skewers(self,alpha,beta):

        self.TAU_rows = density_to_tau(self.DENSITY_DELTA_rows+1,alpha,beta)
        self.tau_computed = True

        return

    #Function to add flux skewers to the object.
    def compute_flux_skewers(self):

        #self.TAU_rows = get_tau(self.Z,self.DENSITY_DELTA_rows+1,alpha,beta)
        self.F_rows = np.exp(-self.TAU_rows)
        #self.F_rows = density_to_flux(self.DENSITY_DELTA_rows+1,alpha,beta)

        #Set the skewers to 1 beyond the quasars.
        for i in range(self.N_qso):
            if self.linear_skewer_RSDs_added == True:
                last_relevant_cell = np.searchsorted(self.Z,self.Z_QSO[i]+self.DZ_RSD[i]) - 1
            else:
                last_relevant_cell = np.searchsorted(self.Z,self.Z_QSO[i]) - 1
            self.F_rows[i,last_relevant_cell+1:] = 1

        self.flux_computed = True

        return

    ## TODO: remove this, now defunct
    #Function to add linear RSDs from the velocity skewers.
    def add_linear_RSDs(self,alpha,beta):

        #add RSDs to these physical density rows
        new_TAU_rows = RSD.add_linear_skewer_RSDs(self.TAU_rows,self.VEL_rows,self.Z)

        ## TODO: find a neater way to do this
        #For the moment, we add a very small value onto the tau skewers, to avoid problems in the inverse lognormal transformation
        #In future, when we don't care about the gaussian skewers, we can get rid of this
        moodified_new_TAU_rows = new_TAU_rows + (new_TAU_rows==0)*1.0e-10

        #convert the new tau rows back to physical density
        new_density_rows = tau_to_density(moodified_new_TAU_rows,alpha,beta)
        new_density_delta_rows = new_density_rows - 1

        #convert the new physical density rows back to gaussian
        new_gaussian_rows = lognormal_delta_to_gaussian(new_density_delta_rows,self.SIGMA_G,self.D)

        #Make a mask where the physical skewers are zero.
        #mask = (new_density_rows != 0)
        #self.IVAR_rows *= mask

        #Overwrite the physical and tau skewers and set a flag to True.
        self.TAU_rows = new_TAU_rows
        self.DENSITY_DELTA_rows = new_density_delta_rows
        self.GAUSSIAN_DELTA_rows = new_gaussian_rows
        self.linear_skewer_RSDs_added = True

        return

    #Function to add thermal RSDs from the velocity skewers.
    def add_RSDs(self,alpha,beta,thermal=True):

        initial_density_rows = 1 + self.DENSITY_DELTA_rows
        new_TAU_rows = RSD.add_skewer_RSDs(self.TAU_rows,initial_density_rows,self.VEL_rows,self.Z,self.R,thermal=thermal)

        ## TODO: find a neater way to do this
        #For the moment, we add a very small value onto the tau skewers, to avoid problems in the inverse lognormal transformation
        #In future, when we don't care about the gaussian skewers, we can get rid of this
        moodified_new_TAU_rows = new_TAU_rows + (new_TAU_rows==0)*1.0e-10

        #convert the new tau rows back to physical density
        new_density_rows = tau_to_density(moodified_new_TAU_rows,alpha,beta)
        new_density_delta_rows = new_density_rows - 1

        #convert the new physical density rows back to gaussian
        new_gaussian_rows = lognormal_delta_to_gaussian(new_density_delta_rows,self.SIGMA_G,self.D)

        #Make a mask where the physical skewers are zero.
        #mask = (new_density_rows != 0)
        #self.IVAR_rows *= mask

        #Overwrite the physical and tau skewers and set a flag to True.
        self.TAU_rows = new_TAU_rows
        self.DENSITY_DELTA_rows = new_density_delta_rows
        self.GAUSSIAN_DELTA_rows = new_gaussian_rows
        self.thermal_skewer_RSDs_added = True

        return


    #Method to combine data from two objects into one.
    # TODO: add something to check that we can just take values from 1 of the objects
    @classmethod
    def combine_files(cls,object_A,object_B,gaussian_only=False):

        N_qso = object_A.N_qso + object_B.N_qso

        """
        something to check N_cells is the same in both files
        """

        N_cells = object_A.N_cells
        SIGMA_G = object_A.SIGMA_G
        ALPHA = object_A.ALPHA

        TYPE = np.concatenate((object_A.TYPE,object_B.TYPE),axis=0)
        RA = np.concatenate((object_A.RA,object_B.RA),axis=0)
        DEC = np.concatenate((object_A.DEC,object_B.DEC),axis=0)
        Z_QSO = np.concatenate((object_A.Z_QSO,object_B.Z_QSO),axis=0)
        DZ_RSD = np.concatenate((object_A.DZ_RSD,object_B.DZ_RSD),axis=0)
        MOCKID = np.concatenate((object_A.MOCKID,object_B.MOCKID),axis=0)
        PLATE = np.concatenate((object_A.PLATE,object_B.PLATE),axis=0)
        MJD = np.concatenate((object_A.MJD,object_B.MJD),axis=0)
        FIBER = np.concatenate((object_A.FIBER,object_B.FIBER),axis=0)

        if not gaussian_only:
            GAUSSIAN_DELTA_rows = np.concatenate((object_A.GAUSSIAN_DELTA_rows,object_B.GAUSSIAN_DELTA_rows),axis=0)
            DENSITY_DELTA_rows = np.concatenate((object_A.DENSITY_DELTA_rows,object_B.DENSITY_DELTA_rows),axis=0)
            VEL_rows = np.concatenate((object_A.VEL_rows,object_B.VEL_rows),axis=0)
            IVAR_rows = np.concatenate((object_A.IVAR_rows,object_B.IVAR_rows),axis=0)
            F_rows = np.concatenate((object_A.F_rows,object_B.F_rows),axis=0)
        else:
            GAUSSIAN_DELTA_rows = np.concatenate((object_A.GAUSSIAN_DELTA_rows,object_B.GAUSSIAN_DELTA_rows),axis=0)
            DENSITY_DELTA_rows = None
            VEL_rows = np.concatenate((object_A.VEL_rows,object_B.VEL_rows),axis=0)
            IVAR_rows = np.concatenate((object_A.IVAR_rows,object_B.IVAR_rows),axis=0)
            F_rows = None

        """
        Something to check this is ok?
        """

        Z = object_A.Z
        LOGLAM_MAP = object_A.LOGLAM_MAP
        R = object_A.R
        D = object_A.D
        V = object_A.V
        A = object_A.A

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Function to save data as a Gaussian colore file.
    def save_as_gaussian_colore(self,location,filename,header,overwrite=False):

        #Organise the data into colore-format arrays.
        colore_1_data = []
        for i in range(self.N_qso):
            colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

        dtype = [('TYPE', 'f8'), ('RA', 'f8'), ('DEC', 'f8'), ('Z_COSMO', 'f8'), ('DZ_RSD', 'f8'), ('MOCKID', int)]
        colore_1 = np.array(colore_1_data,dtype=dtype)
        colore_2 = self.GAUSSIAN_DELTA_rows
        colore_3 = self.VEL_rows

        colore_4_data = []
        for i in range(self.N_cells):
            colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

        dtype = [('R', 'f8'), ('Z', 'f8'), ('D', 'f8'), ('V', 'f8')]
        colore_4 = np.array(colore_4_data,dtype=dtype)

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_CATALOG = fits.ColDefs(colore_1)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')
        hdu_GAUSSIAN = fits.ImageHDU(data=colore_2,header=header,name='GAUSSIAN_DELTA')
        hdu_VEL = fits.ImageHDU(data=colore_3,header=header,name='VELOCITY')
        cols_COSMO = fits.ColDefs(colore_4)
        hdu_COSMO = fits.BinTableHDU.from_columns(cols_COSMO,header=header,name='COSMO')

        #Combine the HDUs into an HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([prihdu, hdu_CATALOG, hdu_GAUSSIAN, hdu_VEL, hdu_COSMO])
        hdulist.writeto(location+filename,overwrite=overwrite)
        hdulist.close

        return

    #Function to save data as a picca density file.
    def save_as_picca_gaussian(self,location,filename,header,overwrite=False,zero_mean_delta=False,min_number_cells=2,mean_DELTA=None):

        lya_lambdas = 10**self.LOGLAM_MAP

        #Determine the relevant QSOs: those that have relevant cells (IVAR > 0) beyond the first_relevant_cell.
        #We impose a minimum number of cells per skewer here to avoid problems with picca.
        relevant_QSOs = []
        for i in range(self.N_qso):
            if np.sum(self.IVAR_rows[i,:]) >= min_number_cells:
                relevant_QSOs += [i]

        #Trim data according to the relevant cells and QSOs.
        relevant_GAUSSIAN_DELTA_rows = self.GAUSSIAN_DELTA_rows[relevant_QSOs,:]
        relevant_IVAR_rows = self.IVAR_rows[relevant_QSOs,:]
        relevant_LOGLAM_MAP = self.LOGLAM_MAP[:]

        #If desired, enforce that the Delta rows have zero mean.
        if zero_mean_delta == True:
            relevant_GAUSSIAN_DELTA_rows = normalise_deltas(relevant_GAUSSIAN_DELTA_rows,mean_DELTA)

        #Organise the data into picca-format arrays.
        picca_0 = relevant_GAUSSIAN_DELTA_rows.T
        picca_1 = relevant_IVAR_rows.T
        picca_2 = relevant_LOGLAM_MAP

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('PLATE', int), ('MJD', 'f8'), ('FIBER', int), ('THING_ID', int)]
        picca_3 = np.array(picca_3_data,dtype=dtype)

        #Make the data into suitable HDUs.
        hdu_DELTA = fits.PrimaryHDU(data=picca_0,header=header)
        hdu_iv = fits.ImageHDU(data=picca_1,header=header,name='IV')
        hdu_LOGLAM_MAP = fits.ImageHDU(data=picca_2,header=header,name='LOGLAM_MAP')
        cols_CATALOG = fits.ColDefs(picca_3)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')

        #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([hdu_DELTA, hdu_iv, hdu_LOGLAM_MAP, hdu_CATALOG])
        hdulist.writeto(location+filename,overwrite=overwrite)
        hdulist.close()

        return

    #Function to save data as a Lognormal colore file.
    def save_as_physical_colore(self,location,filename,header):

        #Organise the data into colore-format arrays.
        colore_1_data = []
        for i in range(self.N_qso):
            colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

        dtype = [('TYPE', 'f8'), ('RA', 'f8'), ('DEC', 'f8'), ('Z_COSMO', 'f8'), ('DZ_RSD', 'f8'), ('MOCKID', int)]
        colore_1 = np.array(colore_1_data,dtype=dtype)

        colore_2 = self.DENSITY_DELTA_rows
        colore_3 = self.VEL_rows

        colore_4_data = []
        for i in range(self.N_cells):
            colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

        dtype = [('R', 'f8'), ('Z', 'f8'), ('D', 'f8'), ('V', 'f8')]
        colore_4 = np.array(colore_4_data,dtype=dtype)

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_CATALOG = fits.ColDefs(colore_1)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')
        hdu_DELTA = fits.ImageHDU(data=colore_2,header=header,name='PHYSICAL_DELTA')
        hdu_VEL = fits.ImageHDU(data=colore_3,header=header,name='VELOCITY')
        cols_COSMO = fits.ColDefs(colore_4)
        hdu_COSMO = fits.BinTableHDU.from_columns(cols_COSMO,header=header,name='COSMO')

        #Combine the HDUs into an HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([prihdu, hdu_CATALOG, hdu_DELTA, hdu_VEL, hdu_COSMO])
        hdulist.writeto(location+filename)
        hdulist.close

        return

    #Function to save data as a picca density file.
    def save_as_picca_density(self,location,filename,header,zero_mean_delta=False,min_number_cells=2,mean_DELTA=None):

        lya_lambdas = 10**self.LOGLAM_MAP

        #Determine the relevant QSOs: those that have relevant cells (IVAR > 0) beyond the first_relevant_cell.
        #We impose a minimum number of cells per skewer here to avoid problems with picca.
        relevant_QSOs = []
        for i in range(self.N_qso):
            if np.sum(self.IVAR_rows[i,:]) >= min_number_cells:
                relevant_QSOs += [i]

        #Trim data according to the relevant cells and QSOs.
        relevant_DENSITY_DELTA_rows = self.DENSITY_DELTA_rows[relevant_QSOs,:]
        relevant_IVAR_rows = self.IVAR_rows[relevant_QSOs,:]
        relevant_LOGLAM_MAP = self.LOGLAM_MAP[:]

        #If desired, enforce that the Delta rows have zero mean.
        if zero_mean_delta == True:
            relevant_DENSITY_DELTA_rows = normalise_deltas(relevant_DENSITY_DELTA_rows,mean_DELTA)

        #Organise the data into picca-format arrays.
        picca_0 = relevant_DENSITY_DELTA_rows.T
        picca_1 = relevant_IVAR_rows.T
        picca_2 = relevant_LOGLAM_MAP

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('PLATE', int), ('MJD', 'f8'), ('FIBER', int), ('THING_ID', int)]
        picca_3 = np.array(picca_3_data,dtype=dtype)

        #Make the data into suitable HDUs.
        hdu_DELTA = fits.PrimaryHDU(data=picca_0,header=header)
        hdu_iv = fits.ImageHDU(data=picca_1,header=header,name='IV')
        hdu_LOGLAM_MAP = fits.ImageHDU(data=picca_2,header=header,name='LOGLAM_MAP')
        cols_CATALOG = fits.ColDefs(picca_3)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')

        #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([hdu_DELTA, hdu_iv, hdu_LOGLAM_MAP, hdu_CATALOG])
        hdulist.writeto(location+filename)
        hdulist.close()

        return

    #Function to save data as a transmission file.
    def save_as_transmission(self,location,filename,header):
        lya_lambdas = 10**self.LOGLAM_MAP

        Z_RSD = self.Z_QSO + self.DZ_RSD

        transmission_1_data = list(zip(self.RA,self.DEC,Z_RSD,self.Z_QSO,self.MOCKID))

        dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('Z_noRSD', 'f8'), ('MOCKID', int)]
        transmission_1 = np.array(transmission_1_data,dtype=dtype)

        transmission_2 = 10**(self.LOGLAM_MAP)
        transmission_3 = self.F_rows

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_METADATA = fits.ColDefs(transmission_1)
        hdu_METADATA = fits.BinTableHDU.from_columns(cols_METADATA,header=header,name='METADATA')
        hdu_WAVELENGTH = fits.ImageHDU(data=transmission_2,header=header,name='WAVELENGTH')
        hdu_TRANSMISSION = fits.ImageHDU(data=transmission_3,header=header,name='TRANSMISSION')

        #Combine the HDUs into an HDUlist (including DLAs, if they have been computed)
        if hasattr(self,'DLA_table') == True:
            hdu_DLAs = fits.hdu.BinTableHDU(data=self.DLA_table,header=header,name='DLA')
            hdulist = fits.HDUList([prihdu, hdu_METADATA, hdu_WAVELENGTH, hdu_TRANSMISSION, hdu_DLAs])
        else:
            hdulist = fits.HDUList([prihdu, hdu_METADATA, hdu_WAVELENGTH, hdu_TRANSMISSION])

        #Save as a new file. Close the HDUlist.
        hdulist.writeto(location+filename)
        hdulist.close()

        return

    #Function to save data as a picca flux file.
    def save_as_picca_flux(self,location,filename,header,min_number_cells = 2,mean_F_data=None):

        lya_lambdas = 10**self.LOGLAM_MAP

        #Determine the relevant QSOs: those that have relevant cells (IVAR > 0) beyond the first_relevant_cell.
        #We impose a minimum number of cells per skewer here to avoid problems with picca.
        relevant_QSOs = []
        for i in range(self.N_qso):
            if np.sum(self.IVAR_rows[i,:]) >= min_number_cells:
                relevant_QSOs += [i]

        #Trim data according to the relevant cells and QSOs.
        relevant_F_rows = self.F_rows[relevant_QSOs,:]
        relevant_IVAR_rows = self.IVAR_rows[relevant_QSOs,:]
        relevant_LOGLAM_MAP = self.LOGLAM_MAP[:]
        relevant_Z = self.Z[:]

        #Calculate mean F as a function of z for the relevant cells, then F_DELTA_rows.
        try:
            mean_F_z_values = mean_F_data[:,0]
            mean_F = mean_F_data[:,1]
            relevant_F_BAR = np.interp(relevant_Z,mean_F_z_values,mean_F)
        except ValueError:
            #This is done with a 'hack' to avoid problems with weights summing to zero.
            small = 1.0e-10
            relevant_F_BAR = np.average(relevant_F_rows,weights=relevant_IVAR_rows+small,axis=0)

        relevant_F_DELTA_rows = ((relevant_F_rows)/relevant_F_BAR - 1)*relevant_IVAR_rows

        #Organise the data into picca-format arrays.
        picca_0 = relevant_F_DELTA_rows.T
        picca_1 = relevant_IVAR_rows.T
        picca_2 = relevant_LOGLAM_MAP

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('PLATE', int), ('MJD', 'f8'), ('FIBER', int), ('THING_ID', int)]
        picca_3 = np.array(picca_3_data,dtype=dtype)

        #Make the data into suitable HDUs.
        hdu_F = fits.PrimaryHDU(data=picca_0,header=header)
        hdu_iv = fits.ImageHDU(data=picca_1,header=header,name='IV')
        hdu_LOGLAM_MAP = fits.ImageHDU(data=picca_2,header=header,name='LOGLAM_MAP')
        cols_CATALOG = fits.ColDefs(picca_3)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')

        #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([hdu_F, hdu_iv, hdu_LOGLAM_MAP, hdu_CATALOG])
        hdulist.writeto(location+filename)
        hdulist.close()

        return

    #Function to save data as a picca velocity file.
    def save_as_picca_velocity(self,location,filename,header,zero_mean_delta=False,min_number_cells=2,overwrite=False):

        lya_lambdas = 10**self.LOGLAM_MAP

        #Determine the relevant QSOs: those that have relevant cells (IVAR > 0) beyond the first_relevant_cell.
        #We impose a minimum number of cells per skewer here to avoid problems with picca.
        relevant_QSOs = []
        for i in range(self.N_qso):
            if np.sum(self.IVAR_rows[i,:]) >= min_number_cells:
                relevant_QSOs += [i]

        #Trim data according to the relevant cells and QSOs.
        relevant_VEL_rows = self.VEL_rows[relevant_QSOs,:]
        relevant_IVAR_rows = self.IVAR_rows[relevant_QSOs,:]
        relevant_LOGLAM_MAP = self.LOGLAM_MAP[:]

        #Organise the data into picca-format arrays.
        picca_0 = relevant_VEL_rows.T
        picca_1 = relevant_IVAR_rows.T
        picca_2 = relevant_LOGLAM_MAP

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('PLATE', int), ('MJD', 'f8'), ('FIBER', int), ('THING_ID', int)]
        picca_3 = np.array(picca_3_data,dtype=dtype)

        #Make the data into suitable HDUs.
        hdu_VEL = fits.PrimaryHDU(data=picca_0,header=header)
        hdu_iv = fits.ImageHDU(data=picca_1,header=header,name='IV')
        hdu_LOGLAM_MAP = fits.ImageHDU(data=picca_2,header=header,name='LOGLAM_MAP')
        cols_CATALOG = fits.ColDefs(picca_3)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')

        #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([hdu_VEL, hdu_iv, hdu_LOGLAM_MAP, hdu_CATALOG])
        hdulist.writeto(location+filename,overwrite=overwrite)
        hdulist.close()

        return

    #Function to save the mean and variance of the different quantities as a function of Z.
    def get_means(self,lambda_min=0.0):

        #Determine the relevant cells and QSOs.
        lya_lambdas = 10**self.LOGLAM_MAP

        #Determine the first cell which corresponds to a lya_line at wavelength > lambda_min
        first_relevant_cell = get_first_relevant_index(lambda_min,lya_lambdas)

        #Determine the furthest cell which is still relevant: i.e. the one in which at least one QSO has non-zero value of IVAR.
        furthest_QSO_index = np.argmax(self.Z_QSO)
        #last_relevant_cell = (np.argmax(self.IVAR_rows[furthest_QSO_index,:]==0) - 1) % self.N_cells
        last_relevant_cell = self.N_cells - 1

        #Determine the relevant QSOs: those that have relevant cells (IVAR > 0) beyond the first_relevant_cell.
        relevant_QSOs = [i for i in range(self.N_qso) if self.IVAR_rows[i,first_relevant_cell] == 1]

        #Trim data according to the relevant cells and QSOs.
        relevant_DENSITY_DELTA_rows = self.DENSITY_DELTA_rows[relevant_QSOs,first_relevant_cell:last_relevant_cell+1]
        relevant_GAUSSIAN_DELTA_rows = self.GAUSSIAN_DELTA_rows[relevant_QSOs,first_relevant_cell:last_relevant_cell+1]
        relevant_F_rows = self.F_rows[relevant_QSOs,first_relevant_cell:last_relevant_cell+1]
        relevant_IVAR_rows = self.IVAR_rows[relevant_QSOs,first_relevant_cell:last_relevant_cell+1]
        relevant_LOGLAM_MAP = self.LOGLAM_MAP[first_relevant_cell:last_relevant_cell+1]

        #For each cell, determine the number of skewers for which it is relevant.
        N_relevant_skewers = np.sum(relevant_IVAR_rows,axis=0)
        relevant_cells = N_relevant_skewers>0

        #Calculate F_DELTA_rows from F_rows.
        #Introduce a small 'hack' in order to get around the problem of having cells with no skewers contributing to them.
        # TODO: find a neater way to deal with this
        small = 1.0e-10
        relevant_F_BAR = np.average(relevant_F_rows,weights=relevant_IVAR_rows+small,axis=0)
        relevant_F_DELTA_rows = ((relevant_F_rows)/relevant_F_BAR - 1)*relevant_IVAR_rows

        #Calculate the mean in each cell of the gaussian delta and its square.
        GDB = np.average(relevant_GAUSSIAN_DELTA_rows,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells
        GDSB = np.average(relevant_GAUSSIAN_DELTA_rows**2,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells

        #Calculate the mean in each cell of the density delta and its square.
        DDB = np.average(relevant_DENSITY_DELTA_rows,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells
        DDSB = np.average(relevant_DENSITY_DELTA_rows**2,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells

        #Calculate the mean in each cell of the flux and its square.
        FB = np.average(relevant_F_rows,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells
        FSB = np.average(relevant_F_rows**2,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells

        #Calculate the mean in each cell of the flux delta and its square.
        FDB = np.average(relevant_F_DELTA_rows,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells
        FDSB = np.average(relevant_F_DELTA_rows**2,weights=relevant_IVAR_rows+small,axis=0)*relevant_cells

        #Stitch together the means into a binary table.
        dtype = [('N', 'f4'),('GAUSSIAN_DELTA', 'f4'), ('GAUSSIAN_DELTA_SQUARED', 'f4'), ('DENSITY_DELTA', 'f4'), ('DENSITY_DELTA_SQUARED', 'f4')
                , ('F', 'f4'), ('F_SQUARED', 'f4'), ('F_DELTA', 'f4'), ('F_DELTA_SQUARED', 'f4')]
        means = np.array(list(zip(N_relevant_skewers,GDB,GDSB,DDB,DDSB,FB,FSB,FDB,FDSB)),dtype=dtype)

        return means

    #Function to add DLAs to a set of skewers.
    def add_DLA_table(self):

        dla_bias = 2.0
        #If extrapolate_z_down is set to a value below the skewer, then we extrapolate down to that value.
        #Otherwise, we start placing DLAs at the start of the skewer.
        extrapolate_z_down = None
        DLA.add_DLA_table_to_object(self,dla_bias=dla_bias,extrapolate_z_down=extrapolate_z_down)

        return


    """
    THE FUNCTIONS BELOW THIS POINT ARE CURRENTLY UNUSED, AND ARE NOT EXPECTED TO BE USED IN FUTURE.

    # TODO: get rid of this function as the one below now covers it
    #Method to extract all data from an input file of a given format.
    @classmethod
    def get_all_data(cls,filename,file_number,input_format,lambda_min=0,IVAR_cutoff=lya,SIGMA_G=None,gaussian_only=False):

        lya = 1215.67
        h = fits.open(filename)

        h_R, h_Z, h_D, h_V = get_COSMO(h,input_format)
        h_lya_lambdas = get_lya_lambdas(h,input_format)

        #Calculate the first_relevant_cell.
        first_relevant_cell = np.argmax(h_lya_lambdas >= lambda_min)

        if input_format == 'physical_colore':

            #Extract data from the HDUlist.
            TYPE = h[1].data['TYPE']
            RA = h[1].data['RA']
            DEC = h[1].data['DEC']
            Z_QSO = h[1].data['Z_COSMO']
            DZ_RSD = h[1].data['DZ_RSD']
            DENSITY_DELTA_rows = h[2].data[:,first_relevant_cell:]
            VEL_rows = h[3].data[:,first_relevant_cell:]
            Z = h[4].data['Z'][first_relevant_cell:]
            R = h[4].data['R'][first_relevant_cell:]
            D = h[4].data['D'][first_relevant_cell:]
            V = h[4].data['V'][first_relevant_cell:]

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = Z.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive the MOCKID and LOGLAM_MAP.
            MOCKID = get_MOCKID(h,input_format,file_number)
            LOGLAM_MAP = np.log10(lya*(1+Z))

            #Calculate the Gaussian skewers.
            GAUSSIAN_DELTA_rows = lognormal_delta_to_gaussian(DENSITY_DELTA_rows,SIGMA_G,D)

            if not gaussian_only:
                #Calculate the transmitted flux.
                A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
                F_rows = np.exp(-TAU_rows)
            else:
                A = None
                ALPHA = None
                TAU_rows = None
                F_rows = None
                DENSITY_DELTA_rows = None

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)

            IVAR_rows = make_IVAR_rows(IVAR_cutoff,Z_QSO,LOGLAM_MAP)

            # TODO: Think about how to do this. Also make sure to implement everwhere!
            #Construct grouping variables for appearance.
            #I =
            #II =
            #III =
            #IV =

        elif input_format == 'gaussian_colore':

            #Extract data from the HDUlist.
            TYPE = h[1].data['TYPE']
            RA = h[1].data['RA']
            DEC = h[1].data['DEC']
            Z_QSO = h[1].data['Z_COSMO']
            DZ_RSD = h[1].data['DZ_RSD']
            GAUSSIAN_DELTA_rows = h[2].data[:,first_relevant_cell:]
            VEL_rows = h[3].data[:,first_relevant_cell:]
            Z = h[4].data['Z'][first_relevant_cell:]
            R = h[4].data['R'][first_relevant_cell:]
            D = h[4].data['D'][first_relevant_cell:]
            V = h[4].data['V'][first_relevant_cell:]

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = Z.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive the MOCKID and LOGLAM_MAP.
            MOCKID = get_MOCKID(h,input_format,file_number)
            LOGLAM_MAP = np.log10(lya*(1+Z))

            if not gaussian_only:
                #Calculate the Gaussian skewers.
                DENSITY_DELTA_rows = gaussian_to_lognormal(GAUSSIAN_DELTA_rows,SIGMA_G,D)

                #Calculate the transmitted flux.
                A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
                F_rows = np.exp(-TAU_rows)
            else:
                A = None
                ALPHA = None
                TAU_rows = None
                F_rows = None
                DENSITY_DELTA_rows = None

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)

            IVAR_rows = make_IVAR_rows(IVAR_cutoff,Z_QSO,LOGLAM_MAP)

        elif input_format == 'picca':

            #Extract data from the HDUlist.
            DENSITY_DELTA_rows = h[0].data.T[:,first_relevant_cell:]
            IVAR_rows = h[1].data.T[:,first_relevant_cell:]
            LOGLAM_MAP = h[2].data[first_relevant_cell:]
            RA = h[3].data['RA']
            DEC = h[3].data['DEC']
            Z_QSO = h[3].data['Z']
            PLATE = h[3].data['PLATE']
            MJD = h[3].data['MJD']
            FIBER = h[3].data['FIBER']
            MOCKID = h[3].data['THING_ID']

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = LOGLAM_MAP.shape[0]
            if SIGMA_G == None:
                SIGMA_G = h[4].header['SIGMA_G']

            #Derive Z.
            Z = (10**LOGLAM_MAP)/lya - 1

            #Calculate the Gaussian skewers.
            GAUSSIAN_DELTA_rows = lognormal_delta_to_gaussian(DENSITY_DELTA_rows,SIGMA_G,D)

            if not gaussian_only:
                #Calculate the transmitted flux.
                A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
                F_rows = np.exp(-TAU_rows)
            else:
                A = None
                ALPHA = None
                TAU_rows = None
                F_rows = None
                DENSITY_DELTA_rows = None

            #Insert placeholder variables for remaining variables.
            TYPE = np.zeros(N_qso)
            DZ_RSD = np.zeros(N_qso)
            R = np.zeros(N_cells)
            D = np.zeros(N_cells)
            V = np.zeros(N_cells)
            VEL_rows = np.zeros((N_qso,N_cells))

        else:
            print('Input format not recognised: current options are "colore" and "picca".')
            print('Please choose one of these options and try again.')

        h.close()

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)



    #Method to create a new object from an existing one, having specified which MOCKIDs we want to include.
    # TODO: add something to check that we can just take values from 1 of the objects
    @classmethod
    def choose_qsos(cls,object_A,MOCKIDs):

        rows = ['']*len(MOCKIDs)
        s = set(MOCKIDs)
        j = 0
        for i, qso in enumerate(object_A.MOCKID):
            if qso in s:
                rows[j] = i
                j=j+1

        N_qso = len(rows)
        N_cells = object_A.N_cells
        SIGMA_G = object_A.SIGMA_G
        ALPHA = object_A.ALPHA

        TYPE = object_A.TYPE[rows]
        RA = object_A.RA[rows]
        DEC = object_A.DEC[rows]
        Z_QSO = object_A.Z_QSO[rows]
        DZ_RSD = object_A.DZ_RSD[rows]
        MOCKID = object_A.MOCKID[rows]
        PLATE = object_A.PLATE[rows]
        MJD = object_A.MJD[rows]
        FIBER = object_A.FIBER[rows]

        GAUSSIAN_DELTA_rows = object_A.GAUSSIAN_DELTA_rows[rows,:]
        DENSITY_DELTA_rows = object_A.DENSITY_DELTA_rows[rows,:]
        VEL_rows = object_A.VEL_rows[rows,:]
        IVAR_rows = object_A.IVAR_rows[rows,:]
        F_rows = object_A.F_rows[rows,:]

        Z = object_A.Z
        LOGLAM_MAP = object_A.LOGLAM_MAP
        R = object_A.R
        D = object_A.D
        V = object_A.V
        A = object_A.A

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Method to create a new object from an existing one, having specified which cells we want to include.
    # TODO: change this so you can specify a z_min/max, or lambda_min/max, rather than just any list of cells. Would need to deal with the case of both z and lambda limits being set.
    @classmethod
    def choose_cells(cls,object_A,cells):

        N_qso = object_A.N_qso
        N_cells = len(cells)
        SIGMA_G = object_A.SIGMA_G
        ALPHA = object_A.ALPHA

        TYPE = object_A.TYPE
        RA = object_A.RA
        DEC = object_A.DEC
        Z_QSO = object_A.Z_QSO
        DZ_RSD = object_A.DZ_RSD
        MOCKID = object_A.MOCKID
        PLATE = object_A.PLATE
        MJD = object_A.MJD
        FIBER = object_A.FIBER

        GAUSSIAN_DELTA_rows = object_A.GAUSSIAN_DELTA_rows[:,cells]
        DENSITY_DELTA_rows = object_A.DENSITY_DELTA_rows[:,cells]
        VEL_rows = object_A.VEL_rows[:,cells]
        IVAR_rows = object_A.IVAR_rows[:,cells]

        Z = object_A.Z[cells]
        LOGLAM_MAP = object_A.LOGLAM_MAP[cells]
        R = object_A.R[cells]
        D = object_A.D[cells]
        V = object_A.V[cells]
        A = object_A.A[cells]

        return cls(N_qso,N_cells,SIGMA_G,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,GAUSSIAN_DELTA_rows,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,R,Z,D,V,LOGLAM_MAP)


    def save(self,filename,header,output_format):

        success = 0
        while success == 0:
            if output_format == 'colore':

                #Organise the data into colore-format arrays.
                colore_1_data = []
                for i in range(self.N_qso):
                    colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

                dtype = [('TYPE', 'f8'), ('RA', 'f8'), ('DEC', 'f8'), ('Z_COSMO', 'f8'), ('DZ_RSD', 'f8'), ('MOCKID', int)]
                colore_1 = np.array(colore_1_data,dtype=dtype)

                colore_2 = self.DENSITY_DELTA_rows
                colore_3 = self.VEL_rows

                colore_4_data = []
                for i in range(self.N_cells):
                    colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

                dtype = [('R', 'f8'), ('Z', 'f8'), ('D', 'f8'), ('V', 'f8')]
                colore_4 = np.array(colore_4_data,dtype=dtype)

                #Construct HDUs from the data arrays.
                prihdr = fits.Header()
                prihdu = fits.PrimaryHDU(header=prihdr)
                cols_CATALOG = fits.ColDefs(colore_1)
                hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')
                hdu_DELTA = fits.ImageHDU(data=colore_2,header=header,name='DELTA')
                hdu_VEL = fits.ImageHDU(data=colore_3,header=header,name='VELOCITY')
                cols_COSMO = fits.ColDefs(colore_4)
                hdu_COSMO = fits.BinTableHDU.from_columns(cols_COSMO,header=header,name='CATALOG')

                #Combine the HDUs into an HDUlist and save as a new file. Close the HDUlist.
                hdulist = fits.HDUList([prihdu, hdu_CATALOG, hdu_DELTA, hdu_VEL, hdu_COSMO])
                hdulist.writeto(filename,overwrite=True)
                hdulist.close

                success = 1

            elif output_format == 'picca':

                #Organise the data into picca-format arrays.
                picca_0 = self.DENSITY_DELTA_rows.T
                picca_1 = self.IVAR_rows.T
                picca_2 = self.LOGLAM_MAP

                picca_3_data = []
                for i in range(self.N_qso):
                    picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

                dtype = [('RA', 'f8'), ('DEC', 'f8'), ('Z', 'f8'), ('PLATE', int), ('MJD', 'f8'), ('FIBER', int), ('MOCKID', int)]
                picca_3 = np.array(picca_3_data,dtype=dtype)

                #Make the data into suitable HDUs.
                hdu_DELTA = fits.PrimaryHDU(data=picca_0,header=header)
                hdu_iv = fits.ImageHDU(data=picca_1,header=header,name='IV')
                hdu_LOGLAM_MAP = fits.ImageHDU(data=picca_2,header=header,name='LOGLAM_MAP')
                cols_CATALOG = fits.ColDefs(picca_3)
                hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')

                #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
                hdulist = fits.HDUList([hdu_DELTA, hdu_iv, hdu_LOGLAM_MAP, hdu_CATALOG])
                hdulist.writeto(filename,overwrite=True)
                hdulist.close()

                success = 1

            else:
                print('Output format "{}" not recognised.\nCurrent options are "colore" and "picca".'.format(output_format))
                output_format = raw_input('Please enter one of these options: ')

        return

    @classmethod
    def crop(cls,object_A,MOCKID,cells):

        rows = ['']*len(MOCKID)
        s = set(MOCKID)
        j = 0
        for i, qso in enumerate(object_A.MOCKID):
            if qso in s:
                rows[j] = i
                j=j+1

        N_qso = len(rows)
        N_cells = len(cells)

        TYPE = object_A.TYPE[rows]
        RA = object_A.RA[rows]
        DEC = object_A.DEC[rows]
        Z_QSO = object_A.Z_QSO[rows]
        DZ_RSD = object_A.DZ_RSD[rows]
        MOCKID = object_A.MOCKID[rows]
        PLATE = object_A.PLATE[rows]
        MJD = object_A.MJD[rows]
        FIBER = object_A.FIBER[rows]

        DENSITY_DELTA_rows = object_A.DENSITY_DELTA_rows[rows,:]
        DENSITY_DELTA_rows = DENSITY_DELTA_rows[:,cells]

        VEL_rows = object_A.VEL_rows[rows,:]
        VEL_rows = VEL_rows[:,cells]

        IVAR_rows = object_A.IVAR_rows[rows,:]
        IVAR_rows = IVAR_rows[:,cells]

        Z = object_A.Z[cells]
        LOGLAM_MAP = object_A.LOGLAM_MAP[cells]
        R = object_A.R[cells]
        D = object_A.D[cells]
        V = object_A.V[cells]

        return cls(N_qso,N_cells,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,R,Z,D,V,LOGLAM_MAP)

    #NOT YET READY TO BE USED - maybe not necessary?
    #Method to extract reduced data from a set of input files of a given format, with a given list of MOCKIDs for each file.
    @classmethod
    def WIP(cls,file_infos,input_format,z_min):


        for file_info in file_infos:

            lya = 1215.67

            h = fits.open(file_info[filename])

            h_MOCKID = get_MOCKID(h,input_format,file_info[file_number])
            h_R, h_Z, h_D, h_V = get_COSMO(h,input_format)

            #Work out which rows in the hdulist we are interested in.
            rows = ['']*len(file_info[MOCKIDs])
            s = set(file_info[MOCKIDs])
            j = 0
            for i, qso in enumerate(h_MOCKID):
                if qso in s:
                    rows[j] = i
                    j = j+1

            #Calculate the first_relevant_cell.
            first_relevant_cell = np.argmax(h_Z >= z_min)

            TYPE = []
            RA = []
            DEC = []
            Z_QSO = []
            DZ_RSD = []
            DENSITY_DELTA_rows = []
            VEL_rows = []
            Z = []
            R = []
            D = []
            V = []
            N_qso = []
            N_cells = []
            MOCKID = []
            LOGLAM_MAP = []
            PLATE = []
            MJD = []
            FIBER = []
            IVAR_rows = []

            if input_format == 'physical_colore':

                #Extract data from the HDUlist.
                TYPE = np.concatenate((TYPE,h[1].data['TYPE'][rows]))
                RA = np.concatenate((RA,h[1].data['RA'][rows]))
                DEC = np.concatenate((DEC,h[1].data['DEC'][rows]))
                Z_QSO = np.concatenate((Z_QSO,h[1].data['Z_COSMO'][rows]))
                DZ_RSD = np.concatenate((DZ_RSD,h[1].data['DZ_RSD'][rows]))

                DENSITY_DELTA_rows = np.concatenate((DENSITY_DELTA_rows,h[2].data[rows,first_relevant_cell:]),axis=0)

                VEL_rows = np.concatenate((VEL_rows,h[3].data[rows,first_relevant_cell:]),axis=0)

                Z = h[4].data['Z'][first_relevant_cell:]
                R = h[4].data['R'][first_relevant_cell:]
                D = h[4].data['D'][first_relevant_cell:]
                V = h[4].data['V'][first_relevant_cell:]

                #Derive the number of quasars and cells in the file.
                N_qso = N_qso + RA.shape[0]
                N_cells = Z.shape[0]

                #Derive the MOCKID and LOGLAM_MAP.
                MOCKID = np.concatenate((MOCKID,h_MOCKID[rows]))
                LOGLAM_MAP = np.log10(lya*(1+Z))

                #Insert placeholder values for remaining variables.
                PLATE = np.concatenate((PLATE,np.zeros(N_qso)))
                MJD = np.concatenate((MJD,np.zeros(N_qso)))
                FIBER = np.concatenate((FIBER,np.zeros(N_qso)))
                IVAR_rows = np.concatenate((IVAR_rows,np.ones((N_qso,N_cells))),axis=0)

            elif input_format == 'picca':

                #Extract data from the HDUlist.
                DENSITY_DELTA_rows = h[0].data.T[rows,first_relevant_cell:]

                IVAR_rows = h[1].data.T[rows,first_relevant_cell:]

                LOGLAM_MAP = h[2].data[first_relevant_cell:]

                RA = h[3].data['RA'][rows]
                DEC = h[3].data['DEC'][rows]
                Z_QSO = h[3].data['Z'][rows]
                PLATE = h[3].data['PLATE'][rows]
                MJD = h[3].data['MJD'][rows]
                FIBER = h[3].data['FIBER'][rows]
                MOCKID = h[3].data['MOCKID'][rows]

                #Derive the number of quasars and cells in the file.
                N_qso = RA.shape[0]
                N_cells = LOGLAM_MAP.shape[0]

                #Derive Z.
                Z = (10**LOGLAM_MAP)/lya - 1

                #Insert placeholder variables for remaining variables.
                TYPE = np.zeros(RA.shape[0])
                R = np.zeros(Z.shape[0])
                D = np.zeros(Z.shape[0])
                V = np.zeros(Z.shape[0])
                DZ_RSD = np.zeros(RA.shape[0])
                VEL_rows = np.zeros(DENSITY_DELTA_rows.shape)

            else:
                print('Input format not recognised: current options are "colore" and "picca".')
                print('Please choose one of these options and try again.')

            h.close()

        return cls(N_qso,N_cells,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,R,Z,D,V,LOGLAM_MAP)
    """
