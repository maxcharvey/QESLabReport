import os
from cbsyst import Csys
import numpy as np
import matplotlib.pyplot as plt
from tools import plot
from tools import helpers
import sys
from QESLabReport6_2 import original_model
from QESLabReport6_3 import acidification_model
from QESLabReport6_4 import ballasting_model


# global variables
V_ocean = 1.34e18  # volume of the ocean in m3
SA_ocean = 358e12  # surface area of the ocean in m2
fSA_hilat = 0.15  # fraction of ocean surface area in 'high latitude' box

# variables used to calculate Q
Q_alpha = 1e-4
Q_beta = 7e-4
Q_k = 8.3e17

# salinity balance - the total amount of salt added or removed to the surface boxes
Fw = 0.1  # low latitude evaporation - precipitation in units of m yr-1
Sref = 35  # reference salinity in units of g kg-1
E = Fw * SA_ocean * (1 - fSA_hilat) * Sref  # amount of salt removed from t low latitude box,  g kg-1 yr-1, ~ kg m-3 yr-1

# NOTE: Initial DIC, TA, PO4 and pCO2 values are set to steady state values from the Ocean Acidification model.

particle_velocity = 10 # m d-1
k_diss = -0.07  # d-1
n_diss = 2.0  # unitless
Omega_crit = 2.5  # unitless
calc_slope = 0.12  # f_CaCO3 / Omega

rho_org = 1200
rho_CaCO3 = 2700


def create_dicts():
    init_hilat = {
        'name': 'hilat',
        'depth': 200,  # box depth, m
        'SA': SA_ocean * fSA_hilat,  # box surface area, m2
        'T': 3.897678,  # initial water temperature, Celcius
        'S': 34.37786,  # initial salinity
        'T_atmos': 0.,  # air temperature, Celcius
        'tau_M': 100.,  # timescale of surface-deep mixing, yr
        'tau_T': 2.,  # timescale of temperature exchange with atmosphere, yr
        'E': -E,  # salt added due to evaporation - precipitation, kg m-3 yr-1
        'tau_CO2': 2.,  # timescale of CO2 exchange, yr
        'DIC': 2.02823,  # Dissolved Inorganic Carbon concentration, mol m-3
        'TA': 2.22043,  # Total Alkalinity, mol m-3
        'tau_PO4': 3.,  # phosphate half life, yr at initial f_CaCO3
        'PO4': 8.90099e-05,  # Phosphate conc, mol m-3
        'f_CaCO3': 0.18134,  # fraction of organic matter export that produces CaCO3 at starting [CO3]
        'k_ballast': 0.0805,
        'rho_particle': 1416.27,
    }
    init_hilat['V'] = init_hilat['SA'] * init_hilat['depth']  # box volume, m3

    init_lolat = {
        'name': 'lolat',
        'depth': 100,  # box depth, m
        'SA': SA_ocean * (1 - fSA_hilat),  # box surface area, m2
        'T': 23.60040,  # initial water temperature, Celcius
        'S': 35.37898,  # initial salinity
        'T_atmos': 25.,  # air temperature, Celcius
        'tau_M': 250.,  # timescale of surface-deep mixing, yr
        'tau_T': 2.,  # timescale of temperature exchange with atmosphere, yr
        'E': E,  # salinity balance, PSU m3 yr-1
        'tau_CO2': 2.,  # timescale of CO2 exchange, yr
        'DIC': 1.99301,  # Dissolved Inorganic Carbon concentration, mol m-3
        'TA': 2.21683,  # Total Alkalinity, mol m-3
        'tau_PO4': 2.,  # phosphate half life, yr at initial f_CaCO3
        'PO4': 1.65460e-04,  # Phosphate conc, mol m-3
        'f_CaCO3': 0.30453,  # fraction of organic matter export that produces CaCO3 at starting [CO3]
        'k_ballast': 0.1609,
        'rho_particle': 1568.14,
    }
    init_lolat['V'] = init_lolat['SA'] * init_lolat['depth']  # box volume, m3

    init_deep = {
        'name': 'deep',
        'V': V_ocean - init_lolat['V'] - init_hilat['V'],  # box volume, m3
        'T': 5.483637,  # initial water temperature, Celcius
        'S': 34.47283,  # initial salinity
        'DIC': 2.32710,  # Dissolved Inorganic Carbon concentration, mol m-3
        'TA': 2.31645,  # Total Alkalinity, mol m-3
        'PO4': 2.30515e-03,  # Phosphate conc, mol m-3
    }

    init_atmos = {
        'name': 'atmos',
        'mass': 5.132e18,  # kg
        'moles_air': 1.736e20,  # moles
        'moles_CO2': 872e15 / 12,  # moles
        'GtC_emissions': 0.0,  # annual emissions of CO2 into the atmosphere, GtC
    }
    init_atmos['pCO2'] = init_atmos['moles_CO2'] / init_atmos['moles_air'] * 1e6

    init_hilat['particle_sinking_time'] = init_hilat['depth'] / particle_velocity
    init_lolat['particle_sinking_time'] = init_lolat['depth'] / particle_velocity

    return [init_lolat, init_hilat, init_deep, init_atmos]


def run1():
    effdicts = create_dicts()
    efflolat, effhilat, effdeep, effatmos = effdicts

    new_fCaCO3 = np.linspace(0, 1, 1000)
    for box in [efflolat, effhilat]:
        v = particle_velocity / (box['rho_particle'] - 1000) * (
                    (rho_org + new_fCaCO3 * (100 / 30) * rho_org) /
                    (1 + new_fCaCO3 * (100 / 30) * (rho_org / rho_CaCO3))
                    - 1000)
        box['particle_sinking_time'] = box['depth'] / v
        export_efficiency = np.exp(-box['k_ballast'] * box['particle_sinking_time'])
        if box == efflolat:
            plt.plot(new_fCaCO3, export_efficiency, c='black', ls='--', label='Low latitude Organic')
            plt.plot(new_fCaCO3, export_efficiency * new_fCaCO3, c='black', ls='-', label='Low latitude CaCO3')
        else:
            plt.plot(new_fCaCO3, export_efficiency, c='blue', ls='--', label='High latitude Organic')
            plt.plot(new_fCaCO3, export_efficiency * new_fCaCO3, c='blue', ls='-', label='High latitude CaCO3')

    plt.legend()
    plt.xlabel('$f_{CaCO_3}$ (unitless)')
    plt.ylabel('Export efficiency (unitless)')

    plt.savefig('QESLabReport16_1', dpi=600)

    plt.show()


def run2():
    vars = ['DIC', 'TA', 'pCO2', 'f_CaCO3', 'GtC_emissions']

    odicts = create_dicts()

    tmax = 3000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = odicts[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emit_atmos['GtC_emissions'][(time > 400) & (time <= 600)] = 8.0

    odicts[3] = emit_atmos

    otime, odicts = original_model(odicts, 3000, 0.5)
    ololat, ohilat, odeep, oatmos = odicts


    oadicts = create_dicts()

    tmax = 3000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = oadicts[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emit_atmos['GtC_emissions'][(time > 400) & (time <= 600)] = 8.0

    oadicts[3] = emit_atmos

    oatime, oadicts = acidification_model(oadicts, 3000, 0.5)
    oalolat, oahilat, oadeep, oaatmos = oadicts


    bldicts = create_dicts()

    tmax = 3000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = bldicts[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emit_atmos['GtC_emissions'][(time > 400) & (time <= 600)] = 8.0

    bldicts[3] = emit_atmos

    bltime, bldicts = ballasting_model(bldicts, 3000, 0.5)
    bllolat, blhilat, bldeep, blatmos = bldicts
    vars = ['DIC', 'TA', 'pCO2', 'f_CaCO3']


    fig, axs = plot.boxes(otime, vars, ololat, ohilat, odeep, oatmos)

    plot.boxes(oatime, vars, oalolat, oahilat, oadeep, oaatmos, axs=axs, ls=':', label='Acidification')
    plot.boxes(bltime, vars, bllolat, blhilat, bldeep, blatmos, axs=axs, ls='--', label='Ballasting')

    axs[0].set_ylabel('DIC ($mol \; m^{-3}$)')
    axs[1].set_ylabel('TA ($mol \; m^{-3}$)')
    axs[2].set_ylabel('$pCO_2$ (ppm)')
    axs[3].set_ylabel('$f_{CaCO_3}$ (unitless)')
    axs[3].set_xlabel('Time (years)')

    axs[2].legend(title='Model', loc='right')
    axs[3].legend(title='Box', loc='right')

    emission = np.linspace(400, 600, 200)
    y_min = [1.5, 2.2, 200, -0.2]
    y_max = [2.5, 2.4, 1200, 0.4]

    for i in range(4):
        axs[i].fill_between(emission, y_max[i], y_min[i], color='lightgray')
        axs[i].set_ylim(y_min[i], y_max[i])

    # y_min = [200, 2.21, 1.9]
    # y_max = [1200, 2.32, 2.45]

    # for i in range(3):
        # axs[i].fill_between(emission, y_max[i], y_min[i], color='lightgray')
        # axs[i].set_ylim(y_min[i], y_max[i])

    plt.savefig('QESLabReport16_2', dpi=600)


    #print(ohilat['DIC'][400], ololat['DIC'][400], odeep['DIC'][400])
    ##print(ohilat['TA'][400], ololat['TA'][400], odeep['TA'][400])
    #print(ohilat['pCO2'][400], ololat['pCO2'][400], oatmos['pCO2'][400])
    #print(oahilat['DIC'][400], oalolat['DIC'][400], oadeep['DIC'][400])
    #print(oahilat['TA'][400], oalolat['TA'][400], oadeep['TA'][400])
    #print(oahilat['pCO2'][400], oalolat['pCO2'][400], oaatmos['pCO2'][400])
    #print(blhilat['DIC'][400], bllolat['DIC'][400], bldeep['DIC'][400])
    #print(blhilat['TA'][400], bllolat['TA'][400], bldeep['TA'][400])
    #print(blhilat['pCO2'][400], bllolat['pCO2'][400], blatmos['pCO2'][400])

    #print(ohilat['DIC'][10000], ololat['DIC'][10000], odeep['DIC'][10000])
    #print(ohilat['TA'][10000], ololat['TA'][10000], odeep['TA'][10000])
    #print(ohilat['pCO2'][10000], ololat['pCO2'][10000], oatmos['pCO2'][10000])
    #print(oahilat['DIC'][10000], oalolat['DIC'][10000], oadeep['DIC'][10000])
    #print(oahilat['TA'][10000], oalolat['TA'][10000], oadeep['TA'][10000])
    #print(oahilat['pCO2'][10000], oalolat['pCO2'][10000], oaatmos['pCO2'][10000])
    #print(blhilat['DIC'][10000], bllolat['DIC'][10000], bldeep['DIC'][10000])
    #print(blhilat['TA'][10000], bllolat['TA'][10000], bldeep['TA'][10000])
    #print(blhilat['pCO2'][10000], bllolat['pCO2'][10000], blatmos['pCO2'][10000])

    #print(ohilat['V'])
    #print(ololat['V'])
    #print(odeep['V'])

    plt.show()


def run3():
    bldicts1 = create_dicts()

    tmax = 1000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = bldicts1[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emit_atmos['GtC_emissions'][(time > 200) & (time <= 400)] = 8.0

    bldicts1[3] = emit_atmos

    bltime1, bldicts1 = ballasting_model(bldicts1, 1000, 0.5)
    bllolat1, blhilat1, bldeep1, blatmos1 = bldicts1

    vars = ['pCO2', 'GtC_emissions']

    fig, axs = plot.boxes(bltime1, vars, bllolat1, blhilat1, bldeep1, blatmos1)

    years_list = [100, 25]
    linestyles = [':', '--']

    for i in range(2):
        bldicts2 = create_dicts()

        tmax = 1000  # how many years to simulate (yr)
        dt = 0.5  # the time step of the simulation (yr)
        time = np.arange(0, tmax + dt, dt)  # the time axis for the model

        emission_amount = 1600 / years_list[i]

        emit_atmos = bldicts2[3].copy()  # create a copy of the original atmosphere input dictionary
        emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
        emit_atmos['GtC_emissions'][(time > 300 - (years_list[i]/2)) & (time <= 300 + (years_list[i]/2))] = emission_amount

        bldicts2[3] = emit_atmos

        bltime2, bldicts2 = ballasting_model(bldicts2, 1000, 0.5)
        bllolat2, blhilat2, bldeep2, blatmos2 = bldicts2

        vars = ['pCO2', 'GtC_emissions']

        plot.boxes(bltime2, vars, bllolat2, blhilat2, bldeep2, blatmos2, axs=axs, ls=linestyles[i], label=f'{years_list[i]} years')

    axs[0].set_ylabel('$pCO_2$ (ppm)')
    axs[1].set_ylabel('Carbon Emissions (GtC)')
    axs[1].set_xlabel('Time (years)')
    axs[0].legend(title='Emission duration (years)', loc='right')
    axs[1].legend(title='Box', loc='right')

    plt.savefig('QESLabReport16_3', dpi=600)

    plt.show()


def run4():
    bldicts1 = create_dicts()

    tmax = 1000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = bldicts1[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emit_atmos['GtC_emissions'][(time > 200) & (time <= 400)] = 8.0

    bldicts1[3] = emit_atmos

    bltime1, bldicts1 = ballasting_model(bldicts1, 1000, 0.5)
    bllolat1, blhilat1, bldeep1, blatmos1 = bldicts1

    vars = ['pCO2', 'GtC_emissions']

    fig, axs = plot.boxes(bltime1, vars, bllolat1, blhilat1, bldeep1, blatmos1, ls='-', lw=0.9)


    bldicts2 = create_dicts()

    tmax = 1000  # how many years to simulate (yr)
    dt = 0.5  # the time step of the simulation (yr)
    time = np.arange(0, tmax + dt, dt)  # the time axis for the model

    emit_atmos = bldicts2[3].copy()  # create a copy of the original atmosphere input dictionary
    emit_atmos['GtC_emissions'] = np.zeros(time.shape)  # creat an array to hold the emission scenario
    emission_phase = np.random.dirichlet(np.ones(400), size=1)
    emission_phase_array = emission_phase.reshape(-1)
    print(sum(emission_phase_array))
    emit_atmos['GtC_emissions'][(time > 200) & (time <= 400)] = emission_phase_array * 3200

    bldicts2[3] = emit_atmos

    bltime2, bldicts2 = ballasting_model(bldicts2, 1000, 0.5)
    bllolat2, blhilat2, bldeep2, blatmos2 = bldicts2

    vars = ['pCO2', 'GtC_emissions']

    plot.boxes(bltime2, vars, bllolat2, blhilat2, bldeep2, blatmos2, axs=axs, ls=':', label='random')

    axs[0].set_ylabel('$pCO_2$ (ppm)')
    axs[1].set_ylabel('Carbon Emissions (GtC)')
    axs[1].set_xlabel('Time (years)')
    axs[0].legend(title='Emission profile', loc='right')
    axs[0].legend(title='Box', loc='right')

    emission = np.linspace(200, 400, 200)
    y_min = [0, 0]
    y_max = [1200, 15]

    for i in range(2):
        axs[i].fill_between(emission, y_max[i], y_min[i], color='lightgray')
        axs[i].set_ylim(y_min[i], y_max[i])

    plt.savefig('QESLabReport16_4', dpi=600)

    plt.show()


if __name__ == "__main__":
    run3()
    run4()
