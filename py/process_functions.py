import numpy as np
from astropy.io import fits
import healpy as hp
import os

lya = 1215.67

#Function to create a 'simulation_data' object given a specific pixel, information about the complete simulation, and the location/filenames of data files.
def make_pixel_object(pixel,original_file_location,original_filename_structure,input_format,master_data,pixel_list,file_number_list,file_pixel_map,z_min):

    print('Working on HEALPix pixel number {} ({} of {})...'.format(pixel,pixel_list.index(pixel)+1,len(pixel_list)))

    #Determine which file numbers we need to look at for the current pixel.
    relevant_file_numbers = [file_number for file_number in file_number_list if file_pixel_map[pixel,file_number]==1]
    files_included = 0

    #For each relevant file, extract the data and aggregate over all files into a 'combined' object.
    for file_number in relevant_file_numbers:
        print(' -> Extracting data from file number {} ({} of {})...'.format(file_number,relevant_file_numbers.index(file_number)+1,len(relevant_file_numbers)))

        #Get the MOCKIDs of the relevant quasars: those that are located in the current pixel, stored in the current file, and have z_qso<z_min.
        relevant_MOCKIDs = [qso['MOCKID'] for qso in master_data if qso['PIXNUM']==pixel and int(number_to_string(qso['MOCKID'],10)[:-7])==file_number]
        N_relevant_qso = len(relevant_MOCKIDs)
        print('    -> {} relevant quasars found.'.format(N_relevant_qso))

        #If there are some relevant quasars, open the data file and make it into a simulation_data object.
        #We use simulation_data.get_reduced_data to avoid loading all of the file's data into the object.
        if N_relevant_qso > 0:
            filename = original_file_location + '/' + original_filename_structure.format(file_number)
            working = simulation_data.get_reduced_data(filename,file_number,input_format,relevant_MOCKIDs)

        #Combine the data from the working file with that from the files already looked at.
        if files_included > 0:
            combined = simulation_data.combine_files(combined,working)
            files_included += 1
        else:
            combined = working
            files_included += 1

    pixel_object = combined
    print('Data extraction completed; {} quasars were found in total.'.format(pixel_object.N_qso))

    return pixel_object

#Function to create a file structure based on a set of numbers, of the form "x//100"/"x".
def make_file_structure(base_location,numbers):

    first_level = []
    for number in numbers:
        first_level += [number//100]

    first_level_set = list(sorted(set(first_level)))

    for i in first_level_set:

        os.mkdir(base_location+str(i))

        for j, number in enumerate(numbers):

            if first_level[j] == i:
                os.mkdir(base_location+str(i)+'/'+str(number))

    return

#Function to convert a list of numbers to a list of n-digit strings.
def number_to_string(number,string_length):

    number_str = str(number)
    if len(number_str)<=string_length:
        string = '0'*(string_length-len(number_str))+number_str
    else:
        exit('The file number is too great to construct a unique MOCKID (more than 3 digits).')

    return string

#Function to extract RA values from a colore or picca format hdulist.
def get_RA(h,input_format):

    if input_format == 'physical_colore':
        RA = h[1].data['RA']
    elif input_format == 'picca':
        RA = h[3].data['RA']
    else:
        print('Error.')

    return RA

#Function to extract DEC values from a colore or picca format hdulist.
def get_DEC(h,input_format):

    if input_format == 'physical_colore':
        DEC = h[1].data['DEC']
    elif input_format == 'picca':
        DEC = h[3].data['DEC']
    else:
        print('Error.')

    return DEC

#Function to extract Z_QSO values from a colore or picca format hdulist.
def get_Z_QSO(h,input_format):

    if input_format == 'physical_colore':
        Z_QSO = h[1].data['Z_COSMO']
    elif input_format == 'picca':
        Z_QSO = h[3].data['Z']
    else:
        print('Error.')

    return Z_QSO

#Function to extract DZ_RSD values from a colore.
def get_DZ_RSD(h,input_format):

    if input_format == 'physical_colore':
        DZ_RSD = h[1].data['DZ_RSD']
    elif input_format == 'picca':
        print('Error: DZ_RSD not stored in picca files.')
    else:
        print('Error.')

    return DZ_RSD

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

    elif input_format == 'picca':

        #Get MOCKID list.
        MOCKID = h[3].data['MOCKID']

    elif input_format == 'ID':

        MOCKID = h[1].data['MOCKID']

    return MOCKID

#Function to construct an array of MOCKIDs given a file_number and a list of row_numbers.
def make_MOCKID(file_number,row_numbers):

    N_qso = len(row_numbers)
    node = '0'*(len(str(file_number))-3) + str(file_number)

    MOCKID = ['']*N_qso
    for i in range(N_qso):
        row_numbers[i] = str(row_numbers[i])
        if len(row_numbers[i])<=7:
            row_numbers[i] = '0'*(7-len(row_numbers[i]))+row_numbers[i]
        else:
            exit('The row number is too great to construct a unique MOCKID (more than 7 digits).')
        MOCKID[i] = int(node+row_numbers[i])

    MOCKID = np.array(MOCKID)

    return MOCKID

#Function to extract Z values from a colore or picca format hdulist.
def get_Z(h,input_format):

    lya = 1215.67

    if input_format == 'physical_colore':
        Z = h[4].data['Z']
    elif input_format == 'picca':
        LOGLAM_MAP = h[2].data
        Z = ((10**LOGLAM_MAP)/lya) - 1
    else:
        print('Error.')

    return Z

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
            pixel_ID[i] = int(hp.pixelfunc.ang2pix(N_side,theta[i],phi[i]))
        else:
            pixel_ID[i] = -1

    return pixel_ID

#Function to extract data suitable for making ID files from a set of colore or picca format files.
def get_ID_data(original_location,original_filename_structure,input_format,file_numbers,N_side):

    ID_data = []
    print('Assembling master data...')
    #Set up the file_pixel_map.
    #file_pixel_map[i,j] is 1 if the jth file contains qsos from the ith pixel, 0 otherwise.
    N_pixels = 12*N_side**2
    file_pixel_map = np.zeros((N_pixels,max(file_numbers)+1))

    for file_number in file_numbers:
        #Open the file and extract the angular coordinate data.
        print(' -> extracting data from {} ({} of {})'.format(original_filename_structure.format(file_number),file_numbers.index(file_number)+1,len(file_numbers)))
        filename = original_location + '/' + original_filename_structure.format(file_number)
        h = fits.open(filename)

        #Extract the component parts of the master file's data from h.
        RA = get_RA(h,input_format)
        DEC = get_DEC(h,input_format)
        Z_QSO_NO_RSD = get_Z_QSO(h,input_format)
        DZ_RSD = get_DZ_RSD(h,input_format)
        MOCKID = get_MOCKID(h,input_format,file_number)

        h.close()

        #Construct the remaining component parts of the master file's data.
        pixel_ID = make_pixel_ID(N_side,RA,DEC)

        #Calculate Z_QSO.
        Z_QSO = Z_QSO_NO_RSD + DZ_RSD

        file_pixel_list = np.sort(list(set(pixel_ID)))
        N_qso = len(MOCKID)

        #Add the MOCKID and pixel_ID from this file to the ID list.
        #for j in range(N_qso):
        #    ID_data += [(MOCKID[j],pixel_ID[j],file_number)]

        ID_data = list(zip(RA,DEC,Z_QSO_NO_RSD,Z_QSO,MOCKID,pixel_ID))

        #Add information to file_pixel_map
        for pixel in file_pixel_list:
            if pixel >= 0:
                file_pixel_map[pixel,file_number]=1

    #Sort the MOCKIDs and pixel_IDs into the right order: first by pixel number, and then by MOCKID.
    dtype = [('RA', '>f4'), ('DEC', '>f4'), ('Z_QSO_NO_RSD', '>f4'), ('Z_QSO', '>f4'), ('MOCKID', int), ('PIXNUM', int)]
    ID = np.array(ID_data, dtype=dtype)
    ID_sort = np.sort(ID, order=['PIXNUM','MOCKID'])

    #Separate the quasars with invalid coordinates from the ID data.
    ID_sort_filter = ID_sort[ID_sort['PIXNUM']>=0]
    ID_sort_bad = ID_sort[ID_sort['PIXNUM']<0]

    return ID_sort_filter, ID_sort_bad, file_pixel_map

#Function to write a single ID file, given the data.
def write_ID(filename,ID_data,N_side):

    #Add appropriate headers and make a table from the data.
    header = fits.Header()
    header['NSIDE'] = N_side
    bt = fits.BinTableHDU.from_columns(ID_data,header=header)

    #Make a primary HDU.
    prihdr = fits.Header()
    prihdu = fits.PrimaryHDU(header=prihdr)

    #Make the .fits file.
    hdulist = fits.HDUList([prihdu,bt])
    hdulist.writeto(filename)
    hdulist.close()

    return

#From lya_mock_p1d.py
def get_tau(z,density):
    """transform lognormal density to optical depth, at each z"""
    # add redshift evolution to mean optical depth
    alpha = 1
    A = 0.374*pow((1+z)/4.0,5.10)

    tau = A*(density**alpha)

    return A, alpha, tau

#Function to make ivar mask
def make_IVAR_rows(lya,Z_QSO,LOGLAM_MAP,N_qso,N_cells):

    lya_lambdas = lya*(1+Z_QSO)
    IVAR_rows = []

    for i in range(N_qso):

        first_not_relevant_cell = np.argmax(10**LOGLAM_MAP > lya_lambdas[i])

        new_IVAR_row = [list(np.concatenate((np.ones(first_not_relevant_cell),np.zeros(N_cells-first_not_relevant_cell))))]
        IVAR_rows += new_IVAR_row

    IVAR_rows = np.array(IVAR_rows)

    return IVAR_rows

#Function to convert lognormal delta skewers (in rows) to gaussian field skewers (in rows).
def lognormal_to_gaussian(LN_DENSITY_DELTA_rows,SIGMA_G,D):

    LN_DENSITY_rows = 1 + LN_DENSITY_DELTA_rows

    GAUSSIAN_rows = np.zeros(LN_DENSITY_rows.shape)

    for j in range(GAUSSIAN_rows.shape[1]):
        GAUSSIAN_rows[:,j] = LN_DENSITY_rows[:,j]/D[j] - (D[j])*(SIGMA_G**2)/2

    return GAUSSIAN_rows

#Function to determine the first index corresponding to a value in an array greater than a minimum value.
def get_first_relevant_index(minimum,values):

    if minimum > 0:
        first_relevant_index = np.argmax(values >= minimum)
    else:
        first_relevant_index = 0

    return first_relevant_index

#Function to determine the indices corresponding to the values in an array greater than a minimum value.
def get_relevant_indices(minimum,values):

    N = values.shape[0]
    relevant_indices = [i for i in range(N) if values[i] > minimum]

    return relevant_indices

#Function to retrieve relevant simulation parameters from the param.cfg file.
def retrieve_simulation_parameters(location,filename):



    return density_type

#Definition of a generic 'simulation_data' class, from which it is easy to save in new formats.
class simulation_data:
    #Initialisation function.
    def __init__(self,N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A):

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

        return

    #Method to extract all data from an input file of a given format.
    @classmethod
    def get_all_data(cls,filename,file_number,input_format,z_min=0):

        lya = 1215.67
        h = fits.open(filename)

        h_Z = get_Z(h,input_format)

        #Calculate the first_relevant_cell.
        first_relevant_cell = np.argmax(h_Z >= z_min)

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
            # TODO: also put in the proper formula once the update has been made to colore!
            SIGMA_G = 1#h[4].header['SIGMA_G']

            #Derive the MOCKID and LOGLAM_MAP.
            MOCKID = get_MOCKID(h,input_format,file_number)
            LOGLAM_MAP = np.log10(lya*(1+Z))
            A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
            F_rows = np.exp(-TAU_rows)

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)
            IVAR_rows = make_IVAR_rows(lya,Z_QSO,LOGLAM_MAP,N_qso,N_cells)

            # TODO: Think about how to do this. Also make sure to implement everwhere!
            #Construct grouping variables for appearance.
            #I =
            #II =
            #III =
            #IV =

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
            MOCKID = h[3].data['MOCKID']

            #Derive the number of quasars and cells in the file.
            N_qso = RA.shape[0]
            N_cells = LOGLAM_MAP.shape[0]

            #Derive Z.
            Z = (10**LOGLAM_MAP)/lya - 1
            A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
            F_rows = np.exp(-TAU_rows)

            """
            Can we calculate DZ_RSD,R,D,V?
            """

            #Insert placeholder variables for remaining variables.
            TYPE = np.zeros(N_qso)
            DZ_RSD = np.zeros(N_qso)
            R = np.zeros(N_cells)
            D = np.zeros(N_cells)
            V = np.zeros(N_cells)
            VEL_rows = np.zeros((N_qso,N_cells))
            # TODO: THIS IS CLEARLY NOT VALID. WORK OUT A WAY TO DO IT BETTER. maybe put it into a header? Or do I really need the read from picca bit?
            SIGMA_G = 0

        else:
            print('Input format not recognised: current options are "colore" and "picca".')
            print('Please choose one of these options and try again.')

        h.close()

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Method to extract reduced data from an input file of a given format, with a given list of MOCKIDs.
    @classmethod
    def get_reduced_data(cls,filename,file_number,input_format,MOCKIDs,z_min=0):

        lya = 1215.67

        h = fits.open(filename)

        h_MOCKID = get_MOCKID(h,input_format,file_number)
        h_Z = get_Z(h,input_format)

        #Work out which rows in the hdulist we are interested in.
        rows = ['']*len(MOCKIDs)
        s = set(MOCKIDs)
        j = 0
        for i, qso in enumerate(h_MOCKID):
            if qso in s:
                rows[j] = i
                j = j+1

        #Calculate the first_relevant_cell.
        first_relevant_cell = np.argmax(h_Z >= z_min)

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
            # TODO: check if this is how the header is labelled
            # TODO: also put in the proper formula once the update has been made to colore!
            SIGMA_G = 1#h[4].header['SIGMA_G']

            #Derive MOCKIDs, LOGLAM_MAP and transmitted flux fraction.
            MOCKID = h_MOCKID[rows]
            LOGLAM_MAP = np.log10(lya*(1+Z))
            A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
            F_rows = np.exp(-TAU_rows)

            #Insert placeholder values for remaining variables.
            PLATE = MOCKID
            MJD = np.zeros(N_qso)
            FIBER = np.zeros(N_qso)
            IVAR_rows = make_IVAR_rows(lya,Z_QSO,LOGLAM_MAP,N_qso,N_cells)

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

            #Derive Z and transmitted flux fraction.
            Z = (10**LOGLAM_MAP)/lya - 1
            A,ALPHA,TAU_rows = get_tau(Z,DENSITY_DELTA_rows+1)
            F_rows = np.exp(-TAU_rows)

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
            # TODO: THIS IS CLEARLY NOT VALID. WORK OUT A WAY TO DO IT BETTER.
            SIGMA_G = 0

        else:
            print('Input format not recognised: current options are "colore" and "picca".')
            print('Please choose one of these options and try again.')

        h.close()

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Method to combine data from two objects into one.
    # TODO: add something to check that we can just take values from 1 of the objects
    @classmethod
    def combine_files(cls,object_A,object_B):

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

        DENSITY_DELTA_rows = np.concatenate((object_A.DENSITY_DELTA_rows,object_B.DENSITY_DELTA_rows),axis=0)
        VEL_rows = np.concatenate((object_A.VEL_rows,object_B.VEL_rows),axis=0)
        IVAR_rows = np.concatenate((object_A.IVAR_rows,object_B.IVAR_rows),axis=0)
        F_rows = np.concatenate((object_A.F_rows,object_B.F_rows),axis=0)

        """
        Something to check this is ok?
        """

        Z = object_A.Z
        LOGLAM_MAP = object_A.LOGLAM_MAP
        R = object_A.R
        D = object_A.D
        V = object_A.V
        A = object_A.A

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Function to save data as a Gaussian colore file.
    def save_as_gaussian_colore(self,location,filename,header):

        #Organise the data into colore-format arrays.
        colore_1_data = []
        for i in range(self.N_qso):
            colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

        dtype = [('TYPE', '>f4'), ('RA', '>f4'), ('DEC', '>f4'), ('Z_COSMO', '>f4'), ('DZ_RSD', '>f4'), ('MOCKID', int)]
        colore_1 = np.array(colore_1_data,dtype=dtype)

        colore_2 = lognormal_to_gaussian(self.DENSITY_DELTA_rows,self.SIGMA_G,self.D)
        colore_3 = self.VEL_rows

        colore_4_data = []
        for i in range(self.N_cells):
            colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

        dtype = [('R', '>f4'), ('Z', '>f4'), ('D', '>f4'), ('V', '>f4')]
        colore_4 = np.array(colore_4_data,dtype=dtype)

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_CATALOG = fits.ColDefs(colore_1)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')
        hdu_GAUSSIAN = fits.ImageHDU(data=colore_2,header=header,name='GAUSSIAN')
        hdu_VEL = fits.ImageHDU(data=colore_3,header=header,name='VELOCITY')
        cols_COSMO = fits.ColDefs(colore_4)
        hdu_COSMO = fits.BinTableHDU.from_columns(cols_COSMO,header=header,name='CATALOG')

        #Combine the HDUs into an HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([prihdu, hdu_CATALOG, hdu_GAUSSIAN, hdu_VEL, hdu_COSMO])
        hdulist.writeto(location+filename)
        hdulist.close

        return

    #Function to save data as a Lognormal colore file.
    def save_as_physical_colore(self,location,filename,header):

        #Organise the data into colore-format arrays.
        colore_1_data = []
        for i in range(self.N_qso):
            colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

        dtype = [('TYPE', '>f4'), ('RA', '>f4'), ('DEC', '>f4'), ('Z_COSMO', '>f4'), ('DZ_RSD', '>f4'), ('MOCKID', int)]
        colore_1 = np.array(colore_1_data,dtype=dtype)

        colore_2 = self.DENSITY_DELTA_rows
        colore_3 = self.VEL_rows

        colore_4_data = []
        for i in range(self.N_cells):
            colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

        dtype = [('R', '>f4'), ('Z', '>f4'), ('D', '>f4'), ('V', '>f4')]
        colore_4 = np.array(colore_4_data,dtype=dtype)

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_CATALOG = fits.ColDefs(colore_1)
        hdu_CATALOG = fits.BinTableHDU.from_columns(cols_CATALOG,header=header,name='CATALOG')
        hdu_DELTA = fits.ImageHDU(data=colore_2,header=header,name='PHYSICAL DELTA')
        hdu_VEL = fits.ImageHDU(data=colore_3,header=header,name='VELOCITY')
        cols_COSMO = fits.ColDefs(colore_4)
        hdu_COSMO = fits.BinTableHDU.from_columns(cols_COSMO,header=header,name='CATALOG')

        #Combine the HDUs into an HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([prihdu, hdu_CATALOG, hdu_DELTA, hdu_VEL, hdu_COSMO])
        hdulist.writeto(location+filename)
        hdulist.close

        return

    #Function to save data as a picca density file.
    def save_as_picca_density(self,location,filename,header,zero_mean_delta=False,lambda_min=0):

        z_min = max(lambda_min/lya - 1, 0)

        first_relevant_cell = get_first_relevant_index(lambda_min,10**self.LOGLAM_MAP)
        relevant_QSOs = get_relevant_indices(z_min,self.Z_QSO)
        print(' -> {} quasars removed from transmission by lambda_min constraint.'.format(self.N_qso-len(relevant_QSOs)))

        #Organise the data into picca-format arrays.
        picca_0 = self.DENSITY_DELTA_rows[relevant_QSOs,first_relevant_cell:].T
        picca_1 = self.IVAR_rows[relevant_QSOs,first_relevant_cell:].T
        picca_2 = self.LOGLAM_MAP[first_relevant_cell:]

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', '>f4'), ('DEC', '>f4'), ('Z', '>f4'), ('PLATE', '>f4'), ('MJD', '>f4'), ('FIBER', '>f4'), ('MOCKID', int)]
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
    def save_as_transmission(self,location,filename,header,lambda_min=0):

        z_min = max(lambda_min/lya - 1, 0)

        first_relevant_cell = get_first_relevant_index(lambda_min,10**self.LOGLAM_MAP)
        relevant_QSOs = get_relevant_indices(z_min,self.Z_QSO)
        print(' -> {} quasars removed from transmission by lambda_min constraint.'.format(self.N_qso-len(relevant_QSOs)))

        #transmission_1_data = []
        #for i in relevant_QSOs:
        #    transmission_1_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.MOCKID[i])]

        transmission_1_data = list(zip(self.RA[relevant_QSOs],self.DEC[relevant_QSOs],self.Z_QSO[relevant_QSOs],self.MOCKID[relevant_QSOs]))

        dtype = [('RA', '>f4'), ('DEC', '>f4'), ('Z', '>f4'), ('MOCKID', int)]
        transmission_1 = np.array(transmission_1_data,dtype=dtype)

        transmission_2 = 10**(self.LOGLAM_MAP)
        transmission_3 = self.F_rows[relevant_QSOs,first_relevant_cell:].T

        #Construct HDUs from the data arrays.
        prihdr = fits.Header()
        prihdu = fits.PrimaryHDU(header=prihdr)
        cols_METADATA = fits.ColDefs(transmission_1)
        hdu_METADATA = fits.BinTableHDU.from_columns(cols_METADATA,header=header,name='METADATA')
        hdu_WAVELENGTH = fits.ImageHDU(data=transmission_2,header=header,name='WAVELENGTH')
        hdu_TRANSMISSION = fits.ImageHDU(data=transmission_3,header=header,name='TRANSMISSION')

        #Combine the HDUs into and HDUlist and save as a new file. Close the HDUlist.
        hdulist = fits.HDUList([prihdu, hdu_METADATA, hdu_WAVELENGTH, hdu_TRANSMISSION])
        hdulist.writeto(location+filename)
        hdulist.close()

        return

    #Function to save data as a picca flux file.
    # TODO: Change F_rows to F_delta_rows here
    def save_as_picca_flux(self,location,filename,header,zero_mean_delta=False,lambda_min=0):

        z_min = max(lambda_min/lya - 1, 0)

        first_relevant_cell = get_first_relevant_index(lambda_min,10**self.LOGLAM_MAP)
        relevant_QSOs = get_relevant_indices(z_min,self.Z_QSO)
        print(' -> {} quasars removed from transmission by lambda_min constraint.'.format(self.N_qso-len(relevant_QSOs)))

        #Organise the data into picca-format arrays.
        picca_0 = self.F_rows[relevant_QSOs,first_relevant_cell:].T + 1
        picca_1 = self.IVAR_rows[relevant_QSOs,first_relevant_cell:].T
        picca_2 = self.LOGLAM_MAP[first_relevant_cell:]

        picca_3_data = []
        for i in range(self.N_qso):
            if i in relevant_QSOs:
                picca_3_data += [(self.RA[i],self.DEC[i],self.Z_QSO[i],self.PLATE[i],self.MJD[i],self.FIBER[i],self.MOCKID[i])]

        dtype = [('RA', '>f4'), ('DEC', '>f4'), ('Z', '>f4'), ('PLATE', '>f4'), ('MJD', '>f4'), ('FIBER', '>f4'), ('MOCKID', int)]
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

        return cls(N_qso,N_cells,SIGMA_G,ALPHA,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,F_rows,R,Z,D,V,LOGLAM_MAP,A)

    #Method to create a new object from an existing one, having specified which cells we want to include.
    # TODO: change this so you can specify a z_min/max, or lambda_min/max, rather than just any list of cells. Would need to deal with the case of both z and lambda limits being set.
    # TODO: add something to check that we can just take values from 1 of the objects
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

        DENSITY_DELTA_rows = object_A.DENSITY_DELTA_rows[:,cells]
        VEL_rows = object_A.VEL_rows[:,cells]
        IVAR_rows = object_A.IVAR_rows[:,cells]

        Z = object_A.Z[cells]
        LOGLAM_MAP = object_A.LOGLAM_MAP[cells]
        R = object_A.R[cells]
        D = object_A.D[cells]
        V = object_A.V[cells]
        A = object_A.A[cells]

        return cls(N_qso,N_cells,SIGMA_G,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,R,Z,D,V,LOGLAM_MAP)


    """
    THE FUNCTIONS BELOW THIS POINT ARE CURRENTLY UNUSED, AND ARE NOT EXPECTED TO BE USED IN FUTURE.
    """

    def save(self,filename,header,output_format):

        success = 0
        while success == 0:
            if output_format == 'colore':

                #Organise the data into colore-format arrays.
                colore_1_data = []
                for i in range(self.N_qso):
                    colore_1_data += [(self.TYPE[i],self.RA[i],self.DEC[i],self.Z_QSO[i],self.DZ_RSD[i],self.MOCKID[i])]

                dtype = [('TYPE', '>f4'), ('RA', '>f4'), ('DEC', '>f4'), ('Z_COSMO', '>f4'), ('DZ_RSD', '>f4'), ('MOCKID', int)]
                colore_1 = np.array(colore_1_data,dtype=dtype)

                colore_2 = self.DENSITY_DELTA_rows
                colore_3 = self.VEL_rows

                colore_4_data = []
                for i in range(self.N_cells):
                    colore_4_data += [(self.R[i],self.Z[i],self.D[i],self.V[i])]

                dtype = [('R', '>f4'), ('Z', '>f4'), ('D', '>f4'), ('V', '>f4')]
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

                dtype = [('RA', '>f4'), ('DEC', '>f4'), ('Z', '>f4'), ('PLATE', '>f4'), ('MJD', '>f4'), ('FIBER', '>f4'), ('MOCKID', int)]
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

        """
        NEED TO GENERATE FILE_INFOS TO PUT INTO THIS
        A DICTIONARY (?) OF FILENAME, FILE_NUMBER AND MOCKIDS
        FORMATS STRING, INTEGER AND LIST
        """

        for file_info in file_infos:

            lya = 1215.67

            h = fits.open(file_info[filename])

            h_MOCKID = get_MOCKID(h,input_format,file_info[file_number])
            h_Z = get_Z(h,input_format)

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

                """
                THIS NEEDS TO BE ADJUSTED IN THE SAME WAY THAT THE COLORE INPUT FORMAT HAS BEEN
                """

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

        return cls(N_qso,N_cells,TYPE,RA,DEC,Z_QSO,DZ_RSD,MOCKID,PLATE,MJD,FIBER,DENSITY_DELTA_rows,VEL_rows,IVAR_rows,R,Z,D,V,LOGLAM_MAP)