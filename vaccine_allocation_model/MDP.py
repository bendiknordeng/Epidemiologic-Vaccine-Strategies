from vaccine_allocation_model.State import State
import numpy as np
from tqdm import tqdm
np.random.seed(10)

class MarkovDecisionProcess:
    def __init__(self, OD_matrices, population, seair, vaccine_supply, horizon, decision_period, policy, infection_boost):
        """ Initializes an instance of the class MarkovDecisionProcess, that administrates

        Parameters
            OD_matrices: Origin-Destination matrices giving movement patterns between regions
            population: A DataFrame with region_id, region_name and population
            seair: A seair model that enables simulation of the decision process
            vaccine_supply: Information about supply of vaccines, shape e.g. (#decision_period, #regions)
            horizon: The amount of decision_periods the decision process is run 
            decision_period: The number of time steps that every decision directly affects
            policy: How the available vaccines should be distributed.
        """
        self.horizon = horizon
        self.OD_matrices = OD_matrices
        self.population = population
        self.vaccine_supply = vaccine_supply
        self.seair = seair
        self.state = self._initialize_state(num_initial_infected=1000, vaccines_available=1000, infection_boost=infection_boost)
        self.path = [self.state]
        self.decision_period = decision_period

        policies = {
            "no_vaccines": self._no_vaccines,
            "random": self._random_policy,
            "population_based": self._population_based_policy,
            "infection_based": self._infection_based_policy
        }

        self.policy = policies[policy]

    def run(self):
        """ Updates states from current time_step to a specified horizon

        Returns
            A path that shows resulting traversal of states
        """
        for _ in range(self.state.time_step, self.horizon):
            print(self.state, end="\n"*3)
            self.update_state()
            if np.sum(self.state.R) / np.sum(self.population.population) > 0.7: # stop if recovered population is 70 % of total population
                break
            if np.sum([self.state.I, self.state.A]) == 0: # stop if infections are zero
                break
        return self.path

    def get_exogenous_information(self, state):
        """ Recieves the exogenous information at time_step t

        Parameters
            t: time_step
            state: state that 
        Returns:
            returns a dictionary of information contain 'alphas', 'vaccine_supply', 'contact_matrices_weights'
        """
        infection_level = self.get_infection_level()
        alphas = self.get_alphas(infection_level)
        contact_matrices_weights = self.get_contact_matrices_weights(infection_level)
        information = {'alphas': alphas, 'vaccine_supply': self.vaccine_supply, 'contact_matrices_weights':contact_matrices_weights}
        return information

    def get_contact_matrices_weights(self, infection_level):
        """ Returns the weight for contact matrices based on compartment values 
        Returns 
            weights for contact matrices
        """
        contact_matrices_weights = np.array([0.31, 0.24, 0.16, 0.29])
        return contact_matrices_weights

    def get_alphas(self, infection_level):
        """ Scales alphas with a given weight for each compartment
        Returns 
            alphas scaled with a weight for each compartment
        """
        alphas = [1, 1, 1, 1, 0.1] # movement for compartments S,E1,E2,A,I
        return alphas
    
    def get_infection_level(self):
        """ Decide what infection level every region is currently at
        Returns
            integer indicating current infection level each region and age group on a scale from 1-3, 3 being most severe
        """
        S, E1, E2, A, I, R, D, V = self.state.get_compartments_values()
        pop_100k = self.population[self.population.columns[2:-1]].to_numpy(dtype="float64")/1e5
        I_per_100k = I/pop_100k
        # np.zeros_like(x)
        # print(f'Max:{np.max(I_per_100k)}')
        # print(f'Min:{np.min(I_per_100k)}')
        # import pdb; pdb.set_trace()
        # TO DO: logic to find infection level
        # calculate I_per_100K per region
        # I_per_100k = 1e5*I/population
        # 0-50 - level 1
        # 50-100 - level 2
        # >100 - level 3
        return 1

    def update_state(self, decision_period=28):
        """ Updates the state of the decision process.

        Parameters
            decision_period: number of periods forward in time that the decision directly affects
        """
        decision = self.policy()
        information = self.get_exogenous_information(self.state)
        self.state = self.state.get_transition(decision, information, self.seair.simulate, decision_period)
        self.path.append(self.state)

    def _initialize_state(self, num_initial_infected, vaccines_available, infection_boost, time_step=0):
        """ Initializes a state, default from the moment a disease breaks out

        Parameters
            initial_infected: array of initial infected (1,356)
            num_initial_infected: number of infected persons to be distributed randomly across regions if initiaL_infected=None e.g 50
            vaccines_available: int, number of vaccines available at time
            infection_boost: array of initial infection boost for each age group
            time_step: timestep in which state is initialized. Should be in the range of (0, (24/time_timedelta)*7 - 1)
        Returns
            an initialized State object, type defined in State.py
        """
        # pop = self.population.population.to_numpy(dtype='float64')
        pop = self.population[self.population.columns[2:-1]].to_numpy(dtype="float64")
        S = pop.copy()
        E1 = np.zeros(pop.shape)
        E2 = np.zeros(pop.shape)
        A = np.zeros(pop.shape)
        I = np.zeros(pop.shape)
        R = np.zeros(pop.shape)
        D = np.zeros(pop.shape)
        V = np.zeros(pop.shape)

        # Boost initial infected
        if infection_boost:
            E1[0] += infection_boost
            S[0] -= infection_boost
            num_initial_infected -= sum(infection_boost)

        initial = S * num_initial_infected/np.sum(pop)
        S -= initial
        E1 += initial

        return State(S, E1, E2, A, I, R, D, V, vaccines_available, E1, time_step) 

    def _no_vaccines(self):
        """ Define allocation of vaccines to zero

        Returns
            a vaccine allocation of shape (#decision periods, #regions, #age_groups)
        """
        pop = self.population[self.population.columns[2:-1]].to_numpy(dtype="float64")
        n_regions, n_age_groups = pop.shape
        return np.zeros(shape=(self.decision_period, n_regions, n_age_groups))

    def _random_policy(self):
        """ Define allocation of vaccines based on random distribution

        Returns
            a vaccine allocation of shape (#decision periods, #regions, #age_groups)
        """
        pop = self.population[self.population.columns[2:-1]].to_numpy(dtype="float64")
        n_regions, n_age_groups = pop.shape
        vaccine_allocation = np.array([np.zeros(pop.shape) for _ in range(self.decision_period)])
        demand = self.state.S.copy()
        vacc_available = self.state.vaccines_available
        while vacc_available > 0:
            period, region, age_group = np.random.randint(self.decision_period), np.random.randint(n_regions), np.random.randint(n_age_groups)
            if demand[region][age_group] > 100: 
                vacc_available -= 1
                vaccine_allocation[period][region][age_group] += 1
                demand[region][age_group] -= 1

        return vaccine_allocation

    def _population_based_policy(self):
        """ Define allocation of vaccines based on number of inhabitants in each region

        Returns
            a vaccine allocation of shape (#decision periods, #regions, #age_groups)
        """
        vaccine_allocation = []
        for period in range(self.decision_period):
            total_allocation = self.state.vaccines_available * self.state.S/np.sum(self.state.S)
            vaccine_allocation.append(total_allocation/self.decision_period)
        return vaccine_allocation

    def _infection_based_policy(self):
        """ Define allocation of vaccines based on number of infected in each region

        Returns
            a vaccine allocation of shape (#decision periods, #regions, #age_groups)
        """
        vaccine_allocation = []
        for period in range(self.decision_period):
            total_allocation = self.state.vaccines_available * self.state.E1/np.sum(self.state.E1)
            vaccine_allocation.append(total_allocation/self.decision_period)
        return vaccine_allocation