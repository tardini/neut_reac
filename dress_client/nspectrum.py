import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import dress
from dress_client import fi_codes

fmt = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s', '%H:%M:%S')
hnd = logging.StreamHandler()
hnd.setFormatter(fmt)
logger = logging.getLogger('DRESS LoS')
logger.addHandler(hnd)
logger.setLevel(logging.DEBUG)

flt = np.float64

       
class nSpectrum:


    def __init__(self, f_in1, f_in2, f_los=None, src='transp', samples_per_volume_element=1e4):

        self.samples_per_volume_element = samples_per_volume_element
        self.code = src

        if src == 'transp':
            self.codeClass = fi_codes.TRANSP2DRESS(f_in1, f_in2)
        elif src == 'ascot':
            self.codeClass = fi_codes.ASCOT2DRESS(f_in1)

        if f_los is None:
            self.dressInput = self.codeClass.code_d
            self.dressInput['solidAngle'] = 4*np.pi*np.ones_like(self.dressInput['dV'])
        else:
            x_m, y_m, z_m, omega, V_m3 = np.loadtxt(f_los, unpack=True)
            R_m = np.hypot(x_m, y_m)
            self.los_dressInput(R_m, z_m)
            self.dressInput['R']  = R_m[self.inside]
            self.dressInput['Z']  = z_m[self.inside]
            self.dressInput['dV'] = V_m3[self.inside]
            self.dressInput['solidAngle'] = omega[self.inside]


    def los_dressInput(self, R_m, z_m):
        '''Mapping quantities from original volumes to LoS volumes. Removing LoS volumes outside a {R, z} domain (separatrix or 2D cartesian grid)'''

        n_los = len(R_m)

# LoS volumes inside R, z domain

        RZ_points = np.hstack((R_m, z_m)).reshape(2, n_los).T
        sepPolygon = np.hstack((self.codeClass.Rbnd, self.codeClass.Zbnd)).reshape(2, len(self.codeClass.Rbnd)).T
        self.sepPath = Path(sepPolygon)
        self.inside = self.sepPath.contains_points(RZ_points)
        logger.debug('Volumes inside Sep %d out of %d', np.sum(self.inside), n_los)

        los2fbm = np.zeros(n_los, dtype=np.int32)
        for jlos in range(n_los):
            if self.inside[jlos]:
                d2 = (self.codeClass.code_d['R'] - R_m[jlos])**2 + (self.codeClass.code_d['Z'] - z_m[jlos])**2
                los2fbm[jlos] = np.argmin(d2)
        los_sep = los2fbm[self.inside]

        self.dressInput = {}
        for key, val in self.codeClass.code_d.items():
            if key in ('E', 'pitch'):
                 self.dressInput[key] = val
            else: # map variables onto LoS volumes
                self.dressInput[key] = val[los_sep]


    def run(self):
        '''Execute DRESS calculation, computing Neutron Emission Spectra: beam-target, thermonuclear, beam-beam'''

        logger.info('Running DRESS')

        Ncells = len(self.dressInput['rho'])

        B_dir = np.atleast_2d([0, -1, 0])
        B_dir = np.repeat(B_dir, Ncells, axis=0)   # B-dir for each spatial location

        if 'v_rot' in self.dressInput.keys():
            v_rot = self.dressInput['v_rot']
        elif 'ang_freq' in self.dressInput.keys():
            v_rot = np.zeros((Ncells, 3), dtype=flt)
            v_rot[:, 1] = self.dressInput['ang_freq']*self.dressInput['R']
        else:
            v_rot = np.zeros((Ncells, 3), dtype=flt)

        dd    = dress.reactions.DDNHe3Reaction()
        scalc = dress.SpectrumCalculator(dd, n_samples=self.samples_per_volume_element)

# Neutron energy bins [keV]
        bin_keV = 10.
        En_bins = np.arange(1500, 3500, bin_keV)    # bin edges
        self.En = 0.5*(En_bins[1:] + En_bins[:-1])  # bin centers

# Compute spectra components

        vols = dress.utils.make_vols(self.dressInput['dV'], self.dressInput['solidAngle'], pos=(self.dressInput['R'], self.dressInput['Z']))
        fast_dist = dress.utils.make_dist('energy-pitch', 'd', Ncells, self.dressInput['density'],
            energy_axis=self.dressInput['E'], pitch_axis=self.dressInput['pitch'], distvals=self.dressInput['F'], ref_dir=B_dir)
        bulk_dist = dress.utils.make_dist('maxwellian', 'd', Ncells, self.dressInput['nd'], temperature=self.dressInput['Ti'], v_collective=v_rot)
        logger.debug('T #nan: %d, #T<=0: %d', np.sum(np.isnan(bulk_dist.T)), np.sum(bulk_dist.T <= 0))
        logger.debug('nd #nan: %d, #nd<=0: %d', np.sum(np.isnan(bulk_dist.density)), np.sum(bulk_dist.density <= 0))

        logger.info('Beam-target')
        self.bt = dress.utils.calc_vols(vols, fast_dist, bulk_dist, scalc, En_bins, integrate=True, quiet=False)

        logger.info('Thermonuclear')
        self.th = dress.utils.calc_vols(vols, bulk_dist, bulk_dist, scalc, En_bins, integrate=True, quiet=False)

        logger.info('Beam-beam')
        self.bb = dress.utils.calc_vols(vols, fast_dist, fast_dist, scalc, En_bins, integrate=True, quiet=False)

        for spec in self.bt, self.bb, self.th:
            spec /= bin_keV
        self.bb *= 0.5
        self.th *= 0.5

        rate_bt = bin_keV*np.sum(self.bt)
        rate_th = bin_keV*np.sum(self.th)
        rate_bb = bin_keV*np.sum(self.bb)
        if hasattr(self, 'inside'): # LoS
            logger.info('b-t rate at detector %12.4e N/s', rate_bt)
            logger.info('th  rate at detector %12.4e N/s', rate_th)
            logger.info('b-b rate at detector %12.4e N/s', rate_bb)
            logger.info('Neutron rate at detector %12.4e N/s', rate_bt + rate_th + rate_bb)
        else: # Total
            logger.info('Total b-t neutrons %12.4e N/s', rate_bt)
            logger.info('Total th  neutrons %12.4e N/s', rate_th)
            logger.info('Total b-b neutrons %12.4e N/s', rate_bb)
            logger.info('Total neutron rate %12.4e N/s', rate_bt + rate_th + rate_bb)


    def storeSpectra(self, f_out='dress_client/output/Spectrum.dat'):
        '''Store ASCII output for DRESS Neutron Emission Spectra'''

        header = 'Eneut      Thermonucl. Beam-target Beam-beam'
        np.savetxt(f_out, np.c_[self.En, self.th, self.bt, self.bb], fmt='%11.4e', header=header)
        logger.info('Stored file %s', f_out)


    def fromFile(self, f_spec):
        '''Read (e.g. for plotting) DRESS ASCII output files, instead of computing Neutron Emission Spectra'''

        self.En, self.th, self.bt, self.bb = np.loadtxt(f_spec, unpack=True, skiprows=1)


    def plotInput(self, jcell=100):
        '''Plot some DRESS input quantities'''

        logger.info('Plotting input')
        plt.figure()
        plt.plot(self.dressInput['rho'], self.dressInput['nd'], 'k+')
        plt.title('Bulk D density')
        plt.xlabel('rho')
        plt.ylabel('density (particles/m^3)')

        plt.figure()
        plt.plot(self.dressInput['rho'], self.dressInput['Ti'], 'go')
        plt.title('Ion temperature')
        plt.xlabel('rho')
        plt.ylabel('temperature (keV)')

        if 'v_rot' in self.dressInput.keys():
            plt.figure()
            plt.plot(self.dressInput['rho'], self.dressInput['v_rot'], 'ro')
            plt.title('Toroidal velocity')
            plt.xlabel('rho')
            plt.ylabel('Toroidal velocity (m/s)')
        else:
            plt.figure()
            plt.plot(self.dressInput['rho'], self.dressInput['ang_freq'], 'ro')
            plt.title('Angular frequency')
            plt.xlabel('rho')
            plt.ylabel('angular frequency (rad/s)')

# Plot fast D density
        plt.figure()
        plt.tripcolor(self.dressInput['R'], self.dressInput['Z'], self.dressInput['density'])
        if hasattr(self, 'sepPath'):
            patch = patches.PathPatch(self.sepPath, facecolor='None', lw=2)
            plt.gca().add_patch(patch)
        plt.title('Fast D density')
        plt.xlabel('R (m)')
        plt.ylabel('Z (m)')
        plt.axis('scaled')

# Plot the (E, pitch) distribution at a given MC cell
        plt.figure()
        R = self.dressInput['R'][jcell]
        Z = self.dressInput['Z'][jcell]
        F = self.dressInput['F'][jcell].T

        plt.pcolor(self.dressInput['E'], self.dressInput['pitch'], F)
        plt.title(f'D distribution at (R, Z) = ({round(R,2)}, {round(Z,2)}) m')
        plt.xlabel('E (keV)')
        plt.ylabel('pitch')


    def plotSpectra(self):
        '''Plot DRESS output Neutron Emission Spectra'''

        logger.info('Plotting LoS spectrum')
        fig = plt.figure()
        if hasattr(self, 'bt'):
            plt.plot(self.En, self.bt, label='BT')
            plt.plot(self.En, self.th, label='TH')
        plt.plot(self.En, self.bb, label='BB')
        ymax = plt.gca().get_ylim()[1]
        plt.plot([2452, 2452], [0, 1.5*ymax], 'k-') # Reference d-d neutron energy
        plt.ylim([0, ymax])
        plt.xlabel('Neutron energy (keV)')
        plt.ylabel('Energy spectrum (neuts/keV/s)')
        if hasattr(self, 'inside'):
            plt.title('Line-of-sight neutron emission spectrum')
        else:
            plt.title('Total neutron emission spectrum')
        plt.legend()
        plt.xlim(2000, 3000)
        return fig
        

if __name__ == '__main__':

    f_los   = 'input/aug_BC501A.los' # Detector LoS file
# TRANSP: plasma, distribution
    f_pl_tr = 'input/36557D05.CDF'
    f_f_tr  = 'input/36557D05_fi_1.cdf'
#ASCOT output
    f_as    = 'input/29795_3.0s_ascot.h5'

# Total spectra
#    spec = nSpectrum(f_pl_tr, f_f_tr, src='transp', samples_per_volume_element=1e3)
    spec = nSpectrum(f_as, f_as, src='ascot', samples_per_volume_element=1e3)

# LoS spectra
#    spec = nSpectrum(f_pl_tr, f_f_tr, f_los=f_los, src='transp', samples_per_volume_element=1e1)
#    spec = nSpectrum(f_as, f_as, f_los=f_los, src='ascot', samples_per_volume_element=1e3)

    spec.run()

#    spec.fromFile('output/tot_tr_mc1e5.dat')
#    spec.fromFile('output/tot_as_mc1e5.dat')
#    spec.fromFile('output/los_tr_mc1e1.dat')
#    spec.fromFile('output/los_tr_mc1e2.dat')
#    spec.fromFile('output/los_tr_mc1e3.dat')
#    spec.fromFile('output/los_as_mc1e1.dat')
#    spec.fromFile('output/los_as_mc1e2.dat')
#    spec.fromFile('output/los_as_mc1e3.dat')

    spec.plotInput()
    spec.plotSpectra()
    spec.storeSpectra()

    plt.show()
