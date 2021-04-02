from vaccine_allocation_model.State import State
import numpy as np
from tqdm import tqdm
import random

class MarkovDecisionProcess:
    def __init__(self, OD_matrices, population, seaiqr, vaccine_supply, horizon, decision_period, policy):
        """ Initializes an instance of the class MarkovDecisionProcess, that administrates

        Parameters
            OD_matrices: Origin-Destination matrices giving movement patterns between regions
            population: A DataFrame with region_id, region_name and population
            seaiqr: A seaiqr model that enables simulation of the decision process
            vaccine_supply: Information about supply of vaccines, shape e.g. (#decision_period, #regions)
            horizon: The amount of decision_periods the decision process is run 
            decision_period: The number of time steps that every decision directly affects
            policy: How the available vaccines should be distributed.
        """
        self.horizon = horizon
        self.OD_matrices = OD_matrices
        self.population = population
        self.vaccine_supply = vaccine_supply
        self.seaiqr = seaiqr
        self.state = self._initialize_state(None, 1000, 1000)
        self.path = [self.state]
        self.decision_period = decision_period

        policies = {
            "random": self._random_policy,
            "population_based": self._population_based_policy
        }

        self.policy = policies[policy]

    def run(self):
        """ Updates states from current time_step to a specified horizon

        Returns
            A path that shows resulting traversal of states
        """
        for _ in tqdm(range(self.state.time_step, self.horizon)):
            self.update_state()
        return self.path

    def get_exogenous_information(self):
        """ Recieves the exogenous information at time_step t

        Parameters
            t: time_step
        Returns:
            returns a vector of alphas indicating the mobility flow at time_step t
        """
        alphas = [np.ones(self.OD_matrices.shape) for x in range(6)]
        information = {'alphas': alphas, 'vaccine_supply': self.vaccine_supply}
        return information
    
    def update_state(self, decision_period=28):
        """ Updates the state of the decision process.

        Parameters
            decision_period: number of periods forward in time that the decision directly affects
        """
        decision = self.policy()
        information = self.get_exogenous_information()
        self.state = self.state.get_transition(decision, information, self.seaiqr.simulate, decision_period)
        self.path.append(self.state)

    def _initialize_state(self, initial_infected, num_initial_infected, vaccines_available, time_step=0):
        """ Initializes a state, default from the moment a disease breaks out

        Parameters
            initial_infected: array of initial infected (1,356)
            num_initial_infected: number of infected persons to be distributed randomly across regions if initiaL_infected=None e.g 50
            vaccines_available: int, number of vaccines available at time
            time_step: timestep in which state is initialized. Should be in the range of (0, (24/time_timedelta)*7 - 1)
        Returns
            an initialized State object, type defined in State.py
        """
        pop = self.population.population.to_numpy(dtype='float64')
        n = len(pop)
        S = pop.copy()
        E = np.zeros(n)
        A = np.zeros(n)
        I = np.zeros(n)
        Q = np.zeros(n)
        R = np.zeros(n)
        D = np.zeros(n)
        V = np.zeros(n)
        H = np.zeros(n)

        if initial_infected is None:
            random.seed(10)
            initial = np.zeros(n)
            for i in range(num_initial_infected):
                loc = np.random.randint(n)
                if i < 5:
                    S[loc]
                    initial[loc]
                if (S[loc] > initial[loc]):
                    initial[loc] += 1.0
        else:
            initial = initial_infected
        assert ((S < initial).sum() == 0)

        S -= initial
        I += initial
        I[0] += 20 # boost infected in Oslo

        return State(S, E, A, I, Q, R, D, V, H, vaccines_available, time_step) 

    def _random_policy(self):
        """ Define allocation of vaccines based on random distribution

        Returns
            a vaccine allocation of shape (#decision periods, #regions)
        """

        n = len(self.population)
        vaccine_allocation = np.array([np.zeros(n) for _ in range(self.decision_period)])
        np.random.seed(10)
        demand = self.state.S
        vacc_available = self.state.vaccines_available
        while vacc_available > 0:
            period, region = np.random.randint(28), np.random.randint(n)
            if demand[region] > 0:
                vacc_available -= 1
                vaccine_allocation[period][region] += 1
                demand[region] -= 1
        
        return vaccine_allocation

    def _population_based_policy(self):
        """ Define allocation of vaccines based on number of inhabitants in each region

        Returns
            a vaccine allocation of shape (#decision periods, #regions)
        """
        n = len(self.population)
        pop = self.population.population.to_numpy(dtype='float64')
        pop_weight = pop/np.sum(pop)
        demand = self.state.S
        region_allocation = pop_weight * self.state.vaccines_available
        for i in range(len(region_allocation)):
            region_allocation[i] = min(region_allocation[i], demand[i]) # throw away unused vaccines (temporary)

        vaccine_allocation = np.array([np.zeros(n) for _ in range(self.decision_period)])
        for period in range(self.decision_period):
            for i, region in enumerate(region_allocation):
                vaccine_allocation[period][i] = region/self.decision_period

        return vaccine_allocation

