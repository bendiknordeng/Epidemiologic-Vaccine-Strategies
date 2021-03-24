from covid import simulation as sim
from covid.seir import SEIR
from vaccine_allocation_model.State import State
import numpy as np
from tqdm import tqdm
import random

class MarkovDecisionProcess:
    def __init__(self, OD_matrices, pop, befolkning, seir, vaccine_supply, horizon, decision_period):
        self.horizon = horizon
        self.OD_matrices = OD_matrices
        self.pop = pop
        self.befolkning = befolkning
        self.vaccine_supply = vaccine_supply
        self.seir = seir
        self.state = self.initialize_state(None, 50, 1000)
        self.path = [self.state]
        self.decision_period = decision_period

    def run_policy(self, policy):
        for t in tqdm(range(self.state.time_step, self.horizon)):
            self.update_state()
        return self.path, self.state

    def get_action(self, policy='random'):
        """ finds the action according to a given state using a given policy 
        Parameters:
            state: current state of type State
            policy: string, name of policy chosen
        Returns:
            array with number of vaccines to allocate to each of the municipalities at time_step t (decision_period, 356)
        """

        n = len(self.pop)
        vaccine_allocation = np.array([np.zeros(n) for _ in range(self.decision_period)])
        if policy=='random':
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

    def get_exogenous_information(self):
        """ recieves the exogenous information at time_step t
        Parameters:
            t: time_step
        Returns:
            returns a vector of alphas indicating the mobility flow at time_step t
        """
        alphas = [np.ones(self.OD_matrices.shape) for x in range(4)]
        information = {'alphas': alphas, 'vaccine_supply': self.vaccine_supply}
        return information
    
    def update_state(self, decision_period=28):
        """ recieves the exogenous information at time_step t
        Parameters:
            state: state
        Returns:
            returns a vector of alphas indicatinig the mobility flow at time_step t
        """
        decision = self.get_action()
        information = self.get_exogenous_information()
        self.path.append(self.state)
        self.state = self.state.get_transition(decision, information, self.seir.simulate, decision_period)

    def initialize_state(self, initial_infected, num_initial_infected, vaccines_available, time_step=0):
        """ initializes a state 
        Parameters
            initial_infected: array of initial infected (1,356)
            num_initial_infected: number of infected persons to be distributed randomly across regions if initiaL_infected=None e.g 50
            vaccines_available: int, number of vaccines available at time
            time_step: timestep in which state is initialized in the range (0, time_timedelta*7-1)
        Returns
            an initialized state object
        """
        n = len(self.pop)
        S = self.pop.copy()
        E = np.zeros(n)
        I = np.zeros(n)
        R = np.zeros(n)
        V = np.zeros(n)
        H = np.zeros(n)

        # Initialize I

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

        return State(S, E, I, R, H, V, vaccines_available, time_step) 


