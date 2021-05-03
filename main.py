from numpy.lib.npyio import save
from covid import plot
from covid import utils
import numpy as np
import pandas as pd
from vaccine_allocation_model.State import State
from vaccine_allocation_model.MDP import MarkovDecisionProcess
from covid.seair import SEAIR
from tqdm import tqdm
from datetime import datetime

if __name__ == '__main__':
    # Get filepaths 
    paths = utils.create_named_tuple('filepaths.txt')

    # Read data and generate parameters
    config = utils.create_named_tuple(paths.config)
    age_labels = utils.generate_labels_from_bins(config.age_bins)
    population = utils.generate_custom_population(config.age_bins, age_labels, paths.age_divided_population, paths.municipalities_names)
    contact_matrices = utils.generate_contact_matrices(config.age_bins, age_labels, population)
    age_group_flow_scaling = utils.get_age_group_flow_scaling(config.age_bins, age_labels, population)
    death_rates = utils.get_age_group_fatality_prob(config.age_bins, age_labels)
    OD_matrices = utils.generate_ssb_od_matrix(28, population, paths.municipalities_commute)
    response_measure_model = utils.load_response_measure_models()
    historic_data = utils.get_historic_data(paths.fhi_data_daily)
    policies = ['random', 'no_vaccines', 'susceptible_based', 'infection_based', 'oldest_first', 'weighted']
    
    # Set initial parameters
    runs = 1
    seeds = np.arange(runs)
    day = 21
    month = 2
    year = 2020
    start_date = utils.get_date(f"{year}{month:02}{day:02}")
    horizon = 60 # number of weeks
    decision_period = 28
    initial_infected = 1000
    initial_vaccines_available = 0
    policy = policies[-1]
    plot_results = runs == 1
    verbose = False
    weighted_policy_weights = [0, 0.33, 0.33, 0.34]
    
    epidemic_function = SEAIR(
                        OD=OD_matrices,
                        contact_matrices=contact_matrices,
                        population=population,
                        age_group_flow_scaling=age_group_flow_scaling,
                        death_rates=death_rates,
                        config=config,
                        paths=paths,
                        write_to_csv=False, 
                        write_weekly=False,
                        include_flow=True,
                        include_waves=True,
                        stochastic=False)

    initial_state = State.initialize_state(
                        num_initial_infected=initial_infected,
                        vaccines_available=initial_vaccines_available,
                        contact_weights=config.initial_contact_weights,
                        alphas=config.initial_alphas,
                        flow_scale=config.initial_flow_scale,
                        population=population,
                        start_date=start_date)
    
    final_states = []
    run_range = tqdm(range(runs)) if runs > 1 else range(runs)
    for i in run_range:
        np.random.seed(seeds[i])
        mdp = MarkovDecisionProcess(
                            config=config,
                            decision_period=decision_period,
                            population=population, 
                            epidemic_function=epidemic_function,
                            initial_state=initial_state,
                            horizon=horizon,
                            policy=policy,
                            weighted_policy_weights=weighted_policy_weights,
                            response_measure_model=response_measure_model,
                            historic_data=historic_data,
                            verbose=verbose)
        mdp.run(runs)
        utils.print_results(mdp.path[-1], population, age_labels, policy, save_to_file=False)
        final_states.append(mdp.path[-1])
    
        yll = utils.get_yll(config.age_bins, age_labels, np.sum(final_states[0].D, axis=0))
        print(f'Years of Life Lost: {yll}')
    
    if runs > 1:
        utils.get_average_results(final_states, population, age_labels, policy, save_to_file=False)

    if plot_results:
        history, new_infections = utils.transform_path_to_numpy(mdp.path)
        plot.plot_control_measures(mdp.path, all=False)

        results_age = history.sum(axis=2)
        plot.age_group_infected_plot_weekly(results_age, start_date, age_labels)
        infection_results_age = new_infections.sum(axis=1)
        plot.age_group_infected_plot_weekly_cumulative(infection_results_age, start_date, age_labels)
        
        # results_compartment = history.sum(axis=3).sum(axis=2)
        # labels = ['S', 'E1', 'E2', 'A', 'I', 'R', 'D', 'V']
        # plot.seir_plot_weekly(results_compartment, start_date, labels)
 
        # utils.get_r_effective(mdp.path, population, config, from_data=False)

        # load necessary data for SEIR development plot
        # df = pd.read_csv(paths.results_history)
        # history = utils.transform_df_to_history(df, 'SEAIQRDVH', 356, 5)
        # results = history.sum(axis=2)
        
        # plot.plot_heatmaps(contact_matrices, config.initial_contact_weights, age_labels, paths.heat_maps)

        # accumulated SEIR development plot
        # plot.seir_plot(results)

            # load necessary data for geospatial plot 
            # kommuner_geometry = plot.create_geopandas(True, population, paths.municipalities_geo_pkl, paths.municipalities_geo_geojson)

            # geospatial plot of simulation
            # plot.plot_simulation(history[::4,:,:], population, results[::4,4], kommuner_geometry, paths.municipality_plots)
            # plot.create_gif(paths.municipality_gif,paths.municipality_plots)

            # geospatial plot of of historical covid cases in Norway
            # history = utils.transform_historical_df_to_history(pd.read_csv(paths.municipalities_hist_data))
            # plot.plot_historical_infected(history[::1,:,:], population, kommuner_geometry, paths.municipality_hist_plots)
            # plot.create_gif(paths.municipality_hist_gif,paths.municipality_hist_plots)

