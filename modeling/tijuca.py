import numpy as np
import astropy.units as u
import astropy.constants as c
import os
import pandas as pd
from astropy.io import fits
import matplotlib.pyplot as plt


def ConvertPlanetMHtoCKStr(m):
    prefixsign = np.sign(m)
    if prefixsign == -1:
        prefix = '-'
    else:
        prefix = '+'
    m = np.abs(m)
    if m / 100 >= 1.0:
        m = prefix+str(m)
    elif m == 0:
        m = '+000'
    else:
        m = prefix+'0'+str(m)
    return m

def ConvertCtoOtoStr(c):
    if c >= 1:
        cc = str(c*100).replace('.0','')
    else:
        cc = '0'+str(c*100).replace('.0','')
    return cc

def ComputeTeq(StarTeff, StarRad, sep, Ab = 0.3, fprime = 1/4):
    ''' from Seager 2016 Exoplanet Atmospheres eqn 3.9
    https://books.google.com/books?id=XpaYJD7IE20C
    '''
    StarRad = StarRad.to(u.km)
    sep = sep.to(u.km)
    return (StarTeff * np.sqrt(StarRad/sep) * ((fprime * (1 - Ab))**(1/4))).value

def GetPhaseAngle(MeanAnom, ecc, inc, argp):
    ''' Function for returning observed phase angle given orbital elements
    Args:
        MeanAnom (flt): Mean anomly in radians, where MeanAnom = orbit fraction*2pi, or M=2pi * time/Period
        ecc (flt): eccentricity, defined on [0,1)
        inc (flt): inclination in degrees, where inc = 90 is edge on, inc = 0 or 180 is face on orbit
        argp (flt): argument of periastron in degrees, defined on [0,360)
        
    Returns:
        flt: phase angle in degrees
    Written by Logan Pearce, 2023
    '''
    import numpy as np
    from myastrotools.tools import danby_solve, eccentricity_anomaly
    inc = np.radians(inc)
    argp = np.radians(argp)
    EccAnom = danby_solve(eccentricity_anomaly, MeanAnom, ecc, 0.001, maxnum=50)
    TrueAnom = 2*np.arctan( np.sqrt( (1+ecc)/(1-ecc) ) * np.tan(EccAnom/2) )
    Alpha = np.arccos( np.sin(inc) * np.sin(TrueAnom + argp) )
    
    return np.degrees(Alpha)

def GetPlanetFlux(PlanetWNO,PlanetFPFS,StarWNO,StarFlux):
    from scipy.interpolate import interp1d
    func = interp1d(StarWNO,StarFlux,fill_value="extrapolate")
    ResampledStarFlux = func(PlanetWNO)
    return ResampledStarFlux*PlanetFPFS

def Make4SpectrumPlot(PlanetWNO,PlanetAlbedo,PlanetFPFS,StarWNO,StarFlux,colormap = 'magma',
                      plotstyle='magrathea'):
    import matplotlib
    plt.style.use(plotstyle)
    cmap = matplotlib.cm.get_cmap(colormap)
    n = 6
    cs = np.linspace(0,1,n)
    colors = cmap(cs)
    
    fig, axs = plt.subplots(2, 2, figsize=(12,10))
    ax1 = axs[0, 0]
    ax2 = axs[0, 1]
    ax3 = axs[1, 0]
    ax4 = axs[1, 1]
    
    ax1.minorticks_on()
    ax1.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    ax1.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)
    ax1.plot(1e4/PlanetWNO, PlanetAlbedo, lw=2, color=colors[1])
    ax1.set_yscale('log')
    #ax1.set_xlabel(r'Wavelength [$\mu$m]')
    ax1.set_ylabel('Planet Albedo')
    ax1.grid(ls=':')
    
    ax2.minorticks_on()
    ax2.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    ax2.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)
    ax2.plot(1e4/PlanetWNO, PlanetFPFS, lw=2, color=colors[2])
    ax2.set_yscale('log')
    #ax2.set_xlabel(r'Wavelength [$\mu$m]')
    ax2.set_ylabel('Planet:Star contrast')
    ax2.grid(ls=':')
    
    ax3.minorticks_on()
    ax3.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    ax3.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)
    ax3.plot(1e4/StarWNO, StarFlux, lw=2, color=colors[3])
    ax3.set_yscale('log')
    ax3.set_xlabel(r'Wavelength [$\mu$m]')
    ax3.set_ylabel(r'Star flux [ergs cm$^{-2}$ s$^{-1}$ cm$^{-1}$]')
    ax3.grid(ls=':')
    
    PlanetFlux = GetPlanetFlux(PlanetWNO,PlanetFPFS,StarWNO,StarFlux)
    ax4.minorticks_on()
    ax4.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    ax4.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)
    ax4.plot(1e4/PlanetWNO, PlanetFlux, lw=2, color=colors[4])
    ax4.set_yscale('log')
    ax4.set_xlabel(r'Wavelength [$\mu$m]')
    ax4.set_ylabel(r'Planet flux [ergs cm$^{-2}$ s$^{-1}$ cm$^{-1}$]')
    ax4.grid(ls=':')
    plt.tight_layout()
    return fig

def ComputeSpectrum(atm_df, pdict, sdict, specdict, calculation = 'planet',
                   saveplots = True, savefiledirectory = None, ComputePlanetFlux = True, make4spectrumplot = True,
                   plotstyle = 'magrathea'):
    
    import picaso.justdoit as jdi
    opacity_db = specdict['opacity_db']
    if opacity_db == None:
        opa_mon = jdi.opannection(wave_range=specdict['wave_range'])
    else:
        opa_mon = jdi.opannection(filename_db = opacity_db, wave_range=specdict['wave_range'])
    spec = jdi.inputs(calculation=calculation)

    spec.phase_angle(phase=pdict['phase']*np.pi/180, num_tangle=pdict['num_tangle'],
                     num_gangle=pdict['num_gangle'])
    if not pdict['gravity']:
        spec.gravity(radius=pdict['radius'], radius_unit=pdict['radius_unit'], 
            mass = pdict['mass'], mass_unit=pdict['mass_unit'])
    else:
        spec.gravity(gravity=pdict['gravity'], gravity_unit=pdict['gravity_unit'])

    # set up star:
    spec.star(opa_mon, temp = sdict['Teff'], metal = np.log10(sdict['mh']), logg = sdict['logg'], 
            radius = sdict['radius'], radius_unit = u.R_sun, 
            semi_major = pdict['semi_major'], semi_major_unit = pdict['semi_major_unit'], database = 'phoenix')

    spec.atmosphere(df=atm_df)
    spec_df = spec.spectrum(opa_mon, 
                            calculation='reflected', 
                            full_output=True)
    wno, alb, fpfs, full_output = spec_df['wavenumber'], spec_df['albedo'], \
                                    spec_df['fpfs_reflected'],  spec_df['full_output']
    wno,fpfs = jdi.mean_regrid(spec_df['wavenumber'],
                          spec_df['fpfs_reflected'], R=specdict['R'])
    wno,alb = jdi.mean_regrid(spec_df['wavenumber'],
                          spec_df['fpfs_reflected'], R=specdict['R'])
    if saveplots:
        plt.style.use(plotstyle)
        # Albedo plot
        plt.figure(figsize=(8,6))
        plt.minorticks_on()
        plt.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
        plt.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)

        plt.plot(1e4/wno, alb, lw=2)

        plt.gca().set_xlabel(r'Wavelength [$\mu$m]')
        plt.gca().set_ylabel('Geo Albedo')
        plt.grid(ls=':')
        plt.tight_layout()
        plt.savefig(savefiledirectory+'/cloud-free-albedo-spectrum-R'+str(specdict['R'])+'.png',
                    bbox_inches='tight')

        # reflected plot
        plt.figure(figsize=(8,6))
        plt.minorticks_on()
        plt.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
        plt.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)

        plt.plot(1e4/wno, fpfs, lw=2)
        plt.gca().set_yscale('log')

        plt.gca().set_xlabel(r'Wavelength [$\mu$m]')
        plt.gca().set_ylabel('Planet:Star contrast')
        plt.grid(ls=':')
        plt.tight_layout()
        plt.savefig(savefiledirectory+'/cloud-free-fpfs-spectrum-R'+str(specdict['R'])+'.png',
                    bbox_inches='tight')
        
    if make4spectrumplot:
        StarWNO,StarFlux = spec.inputs['star']['wno'],spec.inputs['star']['flux']
        fig = Make4SpectrumPlot(wno,alb,fpfs,StarWNO,StarFlux,colormap = 'magma')
        fig.savefig(savefiledirectory+'/cloud-free-4SpectrumPlot-R'+str(specdict['R'])+'.png',
                    bbox_inches='tight')
        
    if ComputePlanetFlux:
        PlanetFlux = GetPlanetFlux(wno, fpfs, StarWNO, StarFlux)
        return wno, alb, fpfs, full_output, PlanetFlux, StarWNO, StarFlux

    
    return wno, alb, fpfs, full_output
    



def MakeModelCloudFreePlanet(pdict, sdict,
                calculation = "planet",
                use_guillotpt = True,
                user_supplied_ptprofile = None,
                cdict = None,
                compute_spectrum = True,
                specdict = None,
                savefiledirectory = None
             ):
    
    ''' Wrapper for PICASO functions for building a cloud-free planet base model
    Args:
        pdict (dict): dictionary of planet parameter inputs
        sdict (dict): dictionary of star parameter inputs
        calculation (str): picaso input for object, "planet" or "brown dwarf"
        use_guillotpt (bool): if True, use Guillot PT approximation. Else user must supply initial PT profile
        user_supplied_ptprofile (df): user supplied pt profile for picaso
        cdict (dict): dictionary of climate run setup params
        specdict (dict): dictionary of spectrum setup params
        savefilename (str): filename and path for the model to be saved.

    Returns:
        pl: picaso planet model inputs
        noclouds: picaso object after climate run before clouds

    Writes to disk:
        terminal_output.txt: text file containing terminal output from run
        recommended-gases.html: bokeh plot fro virga of recommended molecules for cloud run
        cloud-free-model.pkl: pickle file of jdi inputs object (pl) and atmosphere (noclouds)
        cloud-free-model-inputs.pkl: pickle file of dictionary inputs pdict, sdict, cdict
        cloud-free-spectrum-full-output-RXXX.pkl: pickle file of dictionary of all spectrum objects - 
                wavenumber, albedo spectrum, planet/star flux contrast, planet flux, star spectrum wavenumber, star flux
        cloud-free-fpfs-spectrum-RXXX.png: plot of planet star flux contrast
        cloud-free-alb-spectrum-RXXX.png: plot of planet albedo spectrum
        cloud-free-4SpectrumPlot-RXXX.png: plot of planet albedo, contrast, star flux, and planet flux
    '''
    import warnings
    warnings.filterwarnings('ignore')
    import picaso.justdoit as jdi
    
    import sys
    import os
    # Make directory to store run results:
    os.system('mkdir '+savefiledirectory)
    
    # Set all terminal output to write to file:
    f = open(savefiledirectory+"/terminal_output.txt", 'w')
    sys.stdout = f
    # Additional info for xarray (not used)
    add_output={
            'author':"Logan Pearce",
            'contact' : "loganpearce1@arizona.edu",
            'code' : "picaso, virga",
            'planet_params':pdict,
            'stellar_params':sdict,
            'orbit_params':{'sma':pdict['semi_major']}
            }
    
    # retrieve opacity correlated k-tables database:
    PlanetMH = pdict['mh']
    PlanetCO = ConvertCtoOtoStr(pdict['CtoO'])
    PlanetMHStr = ConvertPlanetMHtoCKStr(pdict['planet_mh_str'])

    if pdict['noTiOVO']:
        ck_db_name = pdict['local_ck_path'] + f'sonora_2020_feh{PlanetMHStr}_co_{PlanetCO}_noTiOVO.data.196'
    else:
        ck_db_name = pdict['local_ck_path'] + f'sonora_2020_feh{PlanetMHStr}_co_{PlanetCO}.data.196'
    print(ck_db_name)
    # Set opacity connection:
    opacity_ck = jdi.opannection(ck_db=ck_db_name, wave_range = specdict['wave_range'])
    
    # initialize model:
    pl = jdi.inputs(calculation= calculation, climate = True)
    
    ### set up planet:
    # input effective temperature
    pl.effective_temp(pdict['tint']) 
    # add gravity:
    if not pdict['gravity']:
        pl.gravity(radius=pdict['radius'], radius_unit=pdict['radius_unit'], 
            mass = pdict['mass'], mass_unit=pdict['mass_unit'])
    else:
        pl.gravity(gravity=pdict['gravity'], gravity_unit=pdict['gravity_unit'])
        
    # set up star:
    pl.star(opacity_ck, temp = sdict['Teff'], metal = np.log10(sdict['mh']), logg = sdict['logg'], 
            radius = sdict['radius'], radius_unit = u.R_sun, 
            semi_major = pdict['semi_major'], semi_major_unit = pdict['semi_major_unit'], database = 'phoenix')
    
    # add phase:
    phase = pdict['phase']
    # If full phase:
    if phase == 0:
        # Use symmetry to speed up calculation.
        num_tangle = 1
        pdict['num_tangle'] = 1
    else:
        num_tangle = pdict['num_tangle']
    pl.phase_angle(phase=phase*np.pi/180, num_tangle=num_tangle, num_gangle=pdict['num_gangle'])
    
    # Add initial P(T) profile guess:
    if use_guillotpt:
        pt = pl.guillot_pt(pdict['Teq'], nlevel=cdict['nlevel'], T_int = pdict['tint'], 
                              p_bottom=cdict['climate_pbottom'], p_top=cdict['climate_ptop'])
    else:
        pt = user_supplied_ptprofile

    # initial PT profile guess:
    temp_guess = pt['temperature'].values 
    press_guess = pt['pressure'].values
    # Input climate params:
    nstr = np.array([0,cdict['nstr_upper'],cdict['nstr_deep'],0,0,0]) # initial guess of convective zones
    # Set up climate run inputs:
    pl.inputs_climate(temp_guess= temp_guess, pressure= press_guess, 
                  nstr = nstr, nofczns = cdict['nofczns'] , rfacv = cdict['rfacv'])
    print('starting climate run')
    # Compute climate:
    noclouds = pl.climate(opacity_ck, save_all_profiles=True, with_spec=True)
    # Set atm to climate run results:
    pl.atmosphere(df=noclouds['ptchem_df'])

    # Generate recommended molecules for clouds:
    from virga import justdoit as vj
    # pressure temp profile from climate run:
    temperature = noclouds['temperature']
    pressure = noclouds['pressure']
    # metallicity = pdict['mh'] #atmospheric metallicity relative to Solar
    metallicity_TEMP = 0 # mh must be 1 for this part
    mmw = 2.2
    # got molecules for cloud species:
    recommended, fig = vj.recommend_gas(pressure, temperature, 10**(metallicity_TEMP), 
                                   mmw, plot=True, outputplot = True)
    import pickle
    pickle.dump(recommended, open(savefiledirectory+'/virga-recommended-molecules.pkl','wb'))
    
    # Save recommended plot for future inspection
    from bokeh.plotting import figure, output_file, save
    output_file(savefiledirectory+"/recomended-gasses.html")
    save(fig)

    # Pickle info and save:
    pickle.dump([pl, noclouds], open(savefiledirectory+'/cloud-free-model.pkl','wb'))
    pickle.dump([pdict, sdict, cdict], open(savefiledirectory+'/cloud-free-model-inputs.pkl','wb'))

    # If you want to compute spectrum here (recommended)
    if compute_spectrum:
        ### Make cloud-free spectrum:
        wno, alb, fpfs, full_output, PlanetFlux, StarWNO, StarFlux = ComputeSpectrum(noclouds['ptchem_df'], pdict, sdict, specdict, 
                                                                  calculation = 'planet',
                                                                  saveplots = True, 
                                                                  savefiledirectory = savefiledirectory, 
                                                                  ComputePlanetFlux = True, 
                                                                  make4spectrumplot = True)
        # dump it out:
        outdict = {'wavenumber':wno, 'albedo spectrum':alb,
                   'planet star contrast':fpfs, 'full output':full_output,
                   'planet flux': PlanetFlux, 'star wavenumber':StarWNO, 'star flux':StarFlux}
        pickle.dump(outdict, 
                    open(savefiledirectory+'/cloud-free-spectrum-full-output-R'+str(specdict['R'])+'.pkl','wb'))
        
    f.close()
    
    return pl, noclouds
    

def MakeModelCloudyPlanet(savefiledirectory, clouddict,
                          calculation = 'planet', 
                         molecules = None):
    
    ''' Wrapper for PICASO functions for building a planet model
    Args:
        savefiledirectory (str): directory containing picaso cloud-free model base case.
        clouddict (dict): dictionary of cloud parameter inputs
        calculation (str): picaso input for object, "planet" or "brown dwarf"
        molecules (list): list of molecules to compute cloud properties. If None, use virga recommended mols
    Returns:
        clouds: picaso planet model inputs
        clouds_added: virga cloud run output clouds
    '''
    # import climate run output:
    import pickle
    import picaso.justdoit as jdi
    
    import sys
    f = open(savefiledirectory+"/terminal_output.txt", 'a')
    sys.stdout = f
    print()
    
    pl, noclouds = pickle.load(open(savefiledirectory+'/cloud-free-model.pkl','rb'))
    pdict, sdict, cdict = pickle.load(open(savefiledirectory+'/cloud-free-model-inputs.pkl','rb'))
    
    opa_mon = jdi.opannection()

    from virga import justdoit as vj
    # pressure temp profile from climate run:
    temperature = noclouds['temperature']
    pressure = noclouds['pressure']
    #metallicity = pdict['mh'] #atmospheric metallicity relative to Solar
    metallicity_TEMP = 0
    # got molecules for cloud species:
    if not molecules:
        # if no user-supplied molecules:
        #get virga recommendation for which gases to run
        # metallicitiy must be in NOT log units
        recommended = vj.recommend_gas(pressure, temperature, 10**(metallicity_TEMP), 
                                       clouddict['mean_mol_weight'],
                        #Turn on plotting
                         plot=False)
        mols = recommended
        print('using virga recommended gas species:',recommended)
    else:
        # otherwise use user supplied mols:
        mols = molecules
    # add atmosphere from climate run:
    atm = noclouds['ptchem_df']
    # add kzz:
    atm['kz'] = [clouddict['kz']]*atm.shape[0]

    # Just set all this up again:
    clouds = jdi.inputs(calculation=calculation) # start a calculation
    clouds.phase_angle(0)
    # add gravity:
    if not pdict['gravity']:
        clouds.gravity(radius=pdict['radius'], radius_unit=pdict['radius_unit'], 
            mass = pdict['mass'], mass_unit=pdict['mass_unit'])
    else:
        clouds.gravity(gravity=pdict['gravity'], gravity_unit=pdict['gravity_unit'])
    # add star:
    clouds.star(opa_mon, temp = sdict['Teff'], metal = sdict['mh'], logg = sdict['logg'], 
        radius = sdict['radius'], radius_unit=u.R_sun, 
        semi_major = pdict['semi_major'], semi_major_unit = pdict['semi_major_unit'])
    # add atmosphere from climate run with kzz:
    clouds.atmosphere(df=atm)
    # get clouds from reference:
    directory ='/Volumes/Oy/virga/virga/reference/RefIndexFiles'
    
    clouds_added = clouds.virga(mols,directory, fsed=clouddict['fsed'], mh=clouddict['mh'],
                         mmw = clouddict['mean_mol_weight'], full_output=True)

    clouddict.update({'condensates':mols})

    pickle.dump(clouds,
                    open(savefiledirectory+'/cloudy-model.pkl','wb'))
    pickle.dump([pdict, sdict, cdict, clouddict],open(savefiledirectory+'/cloudy-model-inputs.pkl','wb'))
    
    f.close()

    return clouds, clouds_added


def MakeModelCloudyAndCloudFreeSpectra(savefiledirectory,
                            spectrum_wavelength_range = [0.5,1.8],
                            spectrum_calculation = 'reflected',
                            spectrum_resolution = 150,
                            calculation = "planet",
                            plot_albedo = False
                                      ):
    
    ''' Wrapper for PICASO functions for building a planet model
    Args:
        savefiledirectory (str): directory containing picaso cloud-free model base case.
        spectrum_wavelength_range (list): range in um of wavelengths to compute spectrum
        spectrum_calculation (str): type of spectrum to calculate
        spectrum_resolution (flt): what R to compute the spectrum
        calculation (str): picaso input for object, "planet" or "brown dwarf"
        plot_albedo (bool): if True, return spectrum in albedo, otherwise return planet/star flux ratio
    Returns:
        clouds: picaso planet model inputs
        clouds_added: virga cloud run output clouds
    '''
    import pickle
    import picaso.justdoit as jdi
    import matplotlib.pyplot as plt

    opa_mon = jdi.opannection(wave_range=spectrum_wavelength_range)
    
    ### Cloud-free spectrum:
    pl, noclouds = pickle.load(open(savefiledirectory+'/cloud-free-model.pkl','rb'))
    pdict, sdict, cdict = pickle.load(open(savefiledirectory+'/cloud-free-model-inputs.pkl','rb'))
    noclouds_spec = jdi.inputs(calculation="planet") # start a calculation
    noclouds_spec.phase_angle(0)
    # add gravity:
    if not pdict['gravity']:
        noclouds_spec.gravity(radius=pdict['radius'], radius_unit=pdict['radius_unit'], 
            mass = pdict['mass'], mass_unit=pdict['mass_unit'])
    else:
        noclouds_spec.gravity(gravity=pdict['gravity'], gravity_unit=pdict['gravity_unit'])
        # add same star:
    noclouds_spec.star(opa_mon, temp = sdict['Teff'], metal = sdict['mh'], logg = sdict['logg'], 
        radius = sdict['radius'], radius_unit=u.R_sun, 
        semi_major = pdict['semi_major'], semi_major_unit = pdict['semi_major_unit'])
    # add new atmosphere computer by climate run:
    noclouds_spec.atmosphere(df=noclouds['ptchem_df'])
    # compute spectrum:
    noclouds_spec_spectrum = noclouds_spec.spectrum(opa_mon, 
                                                    calculation=spectrum_calculation, 
                                                    full_output=True)
    if plot_albedo:
        w_noclouds, f_noclouds = jdi.mean_regrid(noclouds_spec_spectrum['wavenumber'],
                              noclouds_spec_spectrum['albedo'], R=spectrum_resolution)
    else:
        w_noclouds, f_noclouds = jdi.mean_regrid(noclouds_spec_spectrum['wavenumber'],
                          noclouds_spec_spectrum['fpfs_reflected'], R=spectrum_resolution)
    
    
    ### Cloud-y spectrum:
    pdict, sdict, cdict, clouddict = pickle.load(open(savefiledirectory+'/cloudy-model-inputs.pkl','rb'))
    clouds_spec = pickle.load(open(savefiledirectory+'/cloudy-model.pkl','rb'))
    clouds_spec_spectrum = clouds_spec.spectrum(opa_mon, 
                    calculation='reflected', 
                    full_output=True)
    if plot_albedo:
        w_clouds, f_clouds = jdi.mean_regrid(clouds_spec_spectrum['wavenumber'],
                              clouds_spec_spectrum['albedo'], R=spectrum_resolution)
    else:
        w_clouds, f_clouds = jdi.mean_regrid(clouds_spec_spectrum['wavenumber'],
                          clouds_spec_spectrum['fpfs_reflected'], R=spectrum_resolution)
        
    pickle.dump([noclouds_spec_spectrum,1e4/w_noclouds, f_noclouds],
               open(savefiledirectory+'/cloud-free-spectrum-R'+str(spectrum_resolution)+'.pkl','wb'))
    pickle.dump([clouds_spec_spectrum,1e4/w_clouds, f_clouds],
               open(savefiledirectory+'/cloudy-spectrum-R'+str(spectrum_resolution)+'.pkl','wb'))
    
    # make plot:
    fig = plt.figure()
    plt.plot(1e4/w_clouds, f_clouds, color='black', label='Cloudy')
    plt.plot(1e4/w_noclouds, f_noclouds, color='darkcyan', label='Cloud-Free')
    plt.minorticks_on()
    plt.tick_params(axis='both',which='major',length =10, width=2,direction='in',labelsize=23)
    plt.tick_params(axis='both',which='minor',length =5, width=2,direction='in',labelsize=23)
    plt.xlabel(r"Wavelength [$\mu$m]", fontsize=25)
    plt.ylabel('Planet:Star Contrast', fontsize=25)
    plt.gca().set_yscale('log')
    plt.grid(ls=':')
    plt.legend(fontsize=15, loc='lower left')
    plt.tight_layout()
    plt.savefig('reflected-spectrum-plot.png', bbox_inches='tight')
    
    return noclouds_spec_spectrum, 1e4/w_noclouds, f_noclouds, clouds_spec_spectrum, 1e4/w_clouds, f_clouds, fig


def RegridSpectrum(directory, file, R):
    ''' Regrid a spectrum
    
    Args:
        directory (str): location of filder containing orginal spectrum
        file (str): pickle file of dataframe of original spectrum. 
                    Ex: /cloud-free-spectrum-full-output-R2000.pkl
        R (flt): R of new spectrum
    
    '''
    import pickle
    import os
    
    df = pickle.load(open(directory+file,'rb'))
    wno, alb, fpfs, full_output = df['wavenumber'], df['albedo'], df['fpfs_reflected'],  df['full_output']
    if 'cloud-free' in file:
        fileout = 'cloud-free-'
    elif 'cloudy' in file:
        fileout = 'cloudy-'
    
    # Albedo plot
    Rwno, Ralb = jdi.mean_regrid(wno, alb , R = R)
    plt.figure()
    plt.figure(figsize=(8,6))
    plt.minorticks_on()
    plt.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    plt.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)

    plt.plot(1e4/Rwno, Ralb, lw=2)

    plt.gca().set_xlabel(r'Wavelength [$\mu$m]')
    plt.gca().set_ylabel('Geo Albedo')
    plt.grid(ls=':')
    plt.tight_layout()
    plt.savefig(directory+fileout + 'albedo-spectrum-R' + R + '.png',bbox_inches='tight')

    # reflected plot
    Rwno, Rfpfs = jdi.mean_regrid(wno, fpfs , R = R)
    plt.figure()
    plt.figure(figsize=(8,6))
    plt.minorticks_on()
    plt.tick_params(axis='both',which='major',length =20, width=2,direction='in',labelsize=23)
    plt.tick_params(axis='both',which='minor',length =10, width=2,direction='in',labelsize=23)

    plt.plot(Rwno, Rfpfs, lw=2)
    plt.gca().set_yscale('log')

    plt.gca().set_xlabel(r'Wavelength [$\mu$m]')
    plt.gca().set_ylabel('Planet:Star contrast')
    plt.grid(ls=':')
    plt.tight_layout()
    plt.savefig(directory+fileout + 'fpfs-spectrum-R' + R + '.png',bbox_inches='tight')

    pickle.dump([wno, alb, fpfs, full_output], open(directory+fileout+'-spectrum-full-output-R' + R + '.pkl','wb'))
    