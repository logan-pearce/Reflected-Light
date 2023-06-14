import numpy as np
#from tools.tools import *
from myastrotools.tijuca import *
import astropy.units as u
import pandas as pandas

def Run1Model(p, num_tangle = 6, num_gangle = 6):

    grid = p['name']
    ## Planet:
    planettype = p['planet_type']
    Tint = p['tint'] # Internal Temperature of your Planet in K
    Teq = ComputeTeq(p['st_teff'], p['rstar']*u.Rsun, p['au']*u.au, 
                     Ab = 0.3, fprime = 1/4) # planet equilibrium temperature 
    radius = p['pl_rad'] #Rjup
    massj = p['pl_mass']
    semi_major = p['au']
    phase = p['phase']

    ## Star:
    T_star = p['st_teff'] # K, star effective temperature
    logg = p['logg'] #logg , cgs
    metal = p['feh'] # metallicity of star
    r_star = p['rstar'] # solar radius


    ## Climate:
    nlevel = p['nlevel'] # number of plane-parallel levels in your code
    nofczns = p['nofczns'] # number of convective zones initially. Let's not play with this for now.
    nstr_upper = p['nstr_upper'] # top most level of guessed convective zone
    nstr_deep = nlevel -2 # this is always the case. Dont change this
    nstr = np.array([0,nstr_upper,nstr_deep,0,0,0]) # initial guess of convective zones
    rfacv = p['rfacv']

    ## Opacities:
    #
    planet_mh = p['mh']
    planet_mh_CtoO = p['cto']

    Teq_str = np.round(Teq, decimals=0)
    directory = f'{grid}-{planettype}-Tstar{T_star}-Rstar{r_star}-Teq{Teq_str}-sep{semi_major}-rad{radius}-mass{massj}-mh{planet_mh}-co{planet_mh_CtoO}-phase{phase}'
    #savefiledirectory = p['output_dir']+directory
    output_dir = ''
    savefiledirectory = output_dir+directory

    local_ck_path = f'/Volumes/Oy/picaso/reference/kcoeff_2020/'
    #local_ck_path = p['local_ck_path']

    planet_properties = {
        'tint':Tint, 'Teq':Teq, 'radius':radius, 'radius_unit':u.Rjup,
         'mass':massj, 'mass_unit': u.Mjup,
         'gravity': None, 'gravity_unit':None,
        'semi_major':semi_major, 'semi_major_unit': u.AU,
        'mh': planet_mh, 'CtoO':planet_mh_CtoO, 'phase':phase, 'num_tangle':num_tangle,
        'num_gangle':num_gangle, 'noTiOVO':p['noTiOVO'], 'planet_mh_str':p['mh_str'],
        'local_ck_path':local_ck_path
    }

    star_properties = {
        'Teff':T_star, 'logg':logg, 'mh':metal, 'radius':r_star
    }

    climate_run_setup = {'climate_pbottom':p['p_bottom'],
            'climate_ptop':p['p_top'],
            'nlevel':nlevel, 'nofczns':nofczns, 'nstr_upper':nstr_upper,
            'nstr_deep':nstr_deep, 'rfacv':rfacv
    }
    #opa_file = p['opa_file']
    opa_file = None
    wave_range = [float(p['wave_range'].split(',')[0].replace('[','')),
              float(p['wave_range'].split(',')[1].replace(' ','').replace(']',''))]
    spectrum_setup = {'opacity_db':opa_file,
                      'wave_range':wave_range,
                      'calculation':'reflected', 'R':150
                     }

    if p['guess'] == 'guillot':
        use_guillotpt = True


    cj = MakeModelCloudFreePlanet(planet_properties, 
                            star_properties,
                            use_guillotpt = True,
                            cdict = climate_run_setup,
                            compute_spectrum = True,
                            specdict = spectrum_setup,
                            savefiledirectory = savefiledirectory
                 )
    return savefiledirectory, cj

def RunGrid(sheet_id='11u2eirdZcWZdjnKFn3vzqbCtKCodstP-KnoGXC5FdR8', 
             sheet_name='GasGiantsBaseModels'):
    import time
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={sheet_name}"
    k = open('ReflectXGasGiantRunReport.txt','w')
    k.close()
    p = pd.read_csv(url)
    p = p.dropna(axis=1, how='all')
    savefiledirectory, cj = Run1Model(p.loc[0])
    with open(savefiledirectory+'/terminal_output.txt','r') as f:
        z = f.read()
        k = open('ReflectXGasGiantRunReport.txt','a')
        t = time.localtime()
        outtime = str(t.tm_year)+'-'+str(t.tm_mon)+'-'+str(t.tm_mday)+'-'+str(t.tm_hour)+':'+str(t.tm_min)+':'+str(t.tm_sec)
        if 'YAY ! ENDING WITH CONVERGENCE' in z:
            k.write(savefiledirectory + ' ' +outtime + '  converged \n')
        else:
            k.write(savefiledirectory + ' ' +outtime + '  FAILED \n')
        k.close()
        
    return p


p = RunGrid()