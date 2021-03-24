from covid.simulation import *
from covid.utils import *
from vaccine_allocation_model.MDP import MarkovDecisionProcess
from collections import namedtuple
from covid.utils import read_config, read_paths


""" if __name__ == '__main__':
    # read filepaths 
    paths = read_paths('filepaths.txt')
    
    # read in data from filepaths 
    config = read_config(paths.config)
    OD_matrices = load_od_matrices(paths.od)
    pop, befolkning = create_population(paths.muncipalities_names, paths.muncipalities_pop)
    seir = initialize_seir(config, pop.shape[1], 50)
    vacc = load_vaccination_programme(OD_matrices.shape[0], pop.shape[1], paths.municipalities_v)
    kommuner_geometry = create_geopandas(True, befolkning, paths.municipalities_geo_pkl, paths.municipalities_geo_geojson)
    
    # simulate seir 
    res = {}   # Dictionary with the results for all cases {}                         
    res['baseline'] = simulate(seir, pop, OD_matrices, vacc)

    # plot seir for all region
    seir_plot(res["baseline"][0])
    
    # declare baseline array storing the dynamics of the compartments 
    baseline = res['baseline'][1][::12, :, :]

    # declare hopsitalisation array storing the dynamics of the hospitalised 
    hosp = res['baseline'][0][::12, 4]

    # geospatial plots 
    plot_simulation(baseline, befolkning, hosp, kommuner_geometry, paths.municipality_plots)

    # generate gif 
    create_gif(paths.municipality_gif,paths.municipality_plots) """


if __name__ == '__main__':
    # read filepaths 
    paths = read_config('filepaths.txt')
    
    # read in data from filepaths 
    config = read_config(paths.config)
    OD_matrices = load_od_matrices(paths.od)
    pop, befolkning = create_population(paths.muncipalities_names, paths.muncipalities_pop)
    seir = initialize_seir(OD_matrices, pop, config)
    vaccine_supply = load_vaccination_programme(OD_matrices.shape[0], len(pop), paths.municipalities_v)

    horizon = 100 # this is number_of_days * periods_per_day 
    mdp = MarkovDecisionProcess(OD_matrices, pop, befolkning, seir, vaccine_supply, horizon, 28)

    path, state = mdp.run_policy("random")
    import pdb; pdb.set_trace()
    
