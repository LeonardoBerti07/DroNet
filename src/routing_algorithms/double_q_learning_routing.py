import random
from src.routing_algorithms.BASE_routing import BASE_routing
from src.utilities import utilities as util
from src.utilities.policies import *
import numpy as np
import math

class DoubleQLearningRouting(BASE_routing):

    def __init__(self, drone, simulator):
        BASE_routing.__init__(self, drone, simulator)
        self.Q_a = np.zeros((16, int(self.simulator.n_drones)))
        self.Q_b = np.zeros((16, int(self.simulator.n_drones)))
        #self.Q = {}
        self.taken_actions = {}
        self.ucb_actions = np.zeros((int(self.simulator.n_drones), int(self.simulator.n_drones)))  #dict for ucb function, instead of taken actions, we don't remove elements from it
        self.num_cells = int((self.simulator.env_height / self.simulator.prob_size_cell) * (self.simulator.env_width / self.simulator.prob_size_cell))
        self.a = simulator.alpha
        self.l = simulator.gamma
        self.div = simulator.div
        self.negReward = simulator.negReward       #setting the hyperparameters for the negative reward
        self.eps = 0
        self.optimistic_value = 0
        self.c = 0
        # self.rnd = np.random.RandomState(self.simulator.seed) #random seed

        self.policy = simulator.policy

        if isinstance(self.policy, UCB):
            self.ucb_actions = np.zeros((int(self.simulator.n_drones)))  # dict for ucb function, instead of taken actions, we don't remove elements from it

        # Riempire tabelle con initial value (2)
        if isinstance(self.policy, Optimistic):
            for drone_id in range(self.simulator.n_drones):
                for cell in range(self.num_cells):
                    for drone_action in range(self.simulator.n_drones):
                        if random.uniform(0, 1) < 0.5:
                            self.Q_a[drone_id, cell, drone_action] = self.optimistic_value
                        else:
                            self.Q_b[drone_id, cell, drone_action] = self.optimistic_value

    def feedback(self, drone, id_event, delay, outcome):
        """
        Feedback returned when the packet arrives at the depot or
        Expire. This function have to be implemented in RL-based protocols ONLY
        @param drone: The drone that holds the packet
        @param id_event: The Event id
        @param delay: packet delay
        @param outcome: -1 or 1 (read below)
        """

        if str(id_event) in self.taken_actions:
            array = self.taken_actions[str(id_event)]
            maxx = -1111111111

            for i in range(len(array)):
                state, action, next_state = array[i]

                #select best action
                if random.uniform(0, 1) < 0.5:
                    for j in range(self.Q_a.shape[1]):
                        if (self.Q_a[next_state, j] > maxx):
                            max_action = j
                            maxx = self.Q_a[next_state, j]
                else:
                    for j in range(self.Q_b.shape[1]):
                        if (self.Q_b[next_state, j] > maxx):
                            max_action = j
                            maxx = self.Q_b[next_state, j]

                #Compute the reward
                if (self.simulator.reward == 2):
                    reward = self.computeReward2(outcome, delay)
                elif (self.simulator.reward==3):
                    reward = self.simulator.computeReward3(outcome, delay)
                else:
                    reward = self.computeReward(outcome, delay)

                #Update Q tables
                if random.uniform(0, 1) < 0.5:
                    self.Q_a[state, action] = self.Q_a[state, action] + self.a * (reward + self.l * self.Q_b[next_state, max_action] - self.Q_a[state, action])
                else:
                    self.Q_b[state, action] = self.Q_b[state, action] + self.a * (reward + self.l * self.Q_a[next_state, max_action] - self.Q_b[state, action])
                    

            #update taken actions
            del self.taken_actions[str(id_event)]

    def computeReward(self, outcome, delay):
        reward = outcome
        if (reward == 1):
            return 1 + reward * (1 / (delay/self.div))               #maggiore ?? l delay minore ?? il reward perch?? vuol dire che abbiamo rischiato l'expire
        else:
            return self.negReward

    def computeReward2(self, outcome, delay):                         #un altro possibile metodo di rewarding
        if outcome == 1:
            return 1 + 1.5 * np.log(2000 - delay)
        else:
            return self.negReward

    def computeReward3(self, outcome, delay):              #same logic as computeReward but with higher values
        if outcome == 1:
            return -(outcome-delay)/10
        else:
            return self.negReward

    def relay_selection(self, opt_neighbors: list, packet):
        """
        This function returns the best relay to send packets.
        @param packet:
        @param opt_neighbors: a list of tuple (hello_packet, source_drone)
        @return: The best drone to use as relay
        """
        #print(self.drone.identifier)
        cell_index = util.TraversedCells.coord_to_cell(size_cell=self.simulator.prob_size_cell,
                                                        width_area=self.simulator.env_width,
                                                        x_pos=self.drone.coords[0],  # e.g. 1500
                                                        y_pos=self.drone.coords[1])[0]  # e.g. 500

        state = int(cell_index)


        next_cell_index = util.TraversedCells.coord_to_cell(size_cell=self.simulator.prob_size_cell,
                                                            width_area=self.simulator.env_width,
                                                            x_pos=self.drone.next_target()[0],
                                                            y_pos=self.drone.next_target()[1])[0]

        next_state = int(next_cell_index)
        chosen = None

        #Select the policy function
        if isinstance(self.policy, Epsilon):
            self.eps = self.policy.epsilon
            chosen = self.egreedy(opt_neighbors, state)

        elif isinstance(self.policy, Optimistic):
            self.optimistic_value = self.policy.optimistic_value
            chosen = self.optimistic(opt_neighbors, state)

        elif isinstance(self.policy, UCB):
            self.c = self.policy.c
            chosen = self.UCB(opt_neighbors, state)


        #Select the id of the chosen drone
        if (chosen == None):
            id = self.drone.identifier
        else:
            id = chosen.identifier


        #Update taken actions
        if (str(packet.event_ref.identifier) in self.taken_actions):            #if I've done the same action with the same packet
            self.taken_actions[str(packet.event_ref.identifier)].append((state, int(id), next_state))
        else:
            self.taken_actions[str(packet.event_ref.identifier)] = [(state, int(id), next_state)]

        #update ucb actions
        if isinstance(self.policy, UCB):
            self.ucb_actions[int(id)] += 1

        return chosen

    '''
    def QLAR(self, state, action, cost):
        # select best action
        for j in self.Q.keys():
            if (self.Q[j] > maxx):
                print(j)
                max_action = int(j[-1])
                maxx = self.Q[j]
                next_state = j[:-1]

        # Update Q table
        self.Q[str(state) + str(action)] = self.Q[str(state) + str(action)] + self.a * (cost + self.l * self.Q[str(next_state), str(max_action)] - self.Q[str(state) + str(action)])

        # Update past state
        self.pastNeig = np.zeros((int(self.simulator.n_drones)))
        for neig in opt:
            drone_id = neig[1].identifier
            self.pastNeig[drone_id] = 1

        self.past_optNeig = opt
        return state
    '''
    def UCB(self,opt_neighbors, state):
        max_a = -10000
        chosen = None
        c = self.policy.c
        for i in range(len(opt_neighbors)):
            drone = opt_neighbors[i][1]
            if random.uniform(0, 1) <0.5:
                Q_t = self.Q_a[state, drone.identifier]
            else:
                Q_t = self.Q_b[state, drone.identifier]
            t = self.simulator.cur_step   #current timestep
            nt_a = self.ucb_actions[drone.identifier]
            exploration_value = (c*math.sqrt((math.log(t)/(nt_a+0.01))))

            if Q_t + exploration_value > max_a:
                max_a = Q_t + exploration_value
                chosen = drone
        return chosen


    def optimistic(self, opt_neighbors, state):
        # Prendere il max
        maxx = -1000000
        chosen = None
        for i in range(len(opt_neighbors)):
            id = int(opt_neighbors[i][1].identifier)
            if random.uniform(0, 1) < 0.5:
                if (self.Q_a[state, id] > maxx):
                    chosen = opt_neighbors[i][1]
                    maxx = self.Q_a[state, id]
            else:
                if (self.Q_b[state, id] > maxx):
                    chosen = opt_neighbors[i][1]
                    maxx = self.Q_b[state, id]

        '''or self.q_b[state, int(self.drone.identifier)'''
        if self.Q_a[state, int(self.drone.identifier)] > maxx:
            chosen = None

        return chosen

    def egreedy(self, opt_neighbors, state):
        r = random.randint(1, 100)
        maxx = -1000000
        if (r > self.eps):
            for i in range(len(opt_neighbors)):
                id = int(opt_neighbors[i][1].identifier)
                if random.uniform(0, 1) < 0.5:
                    if (self.Q_a[state, id] > maxx):
                        chosen = opt_neighbors[i][1]
                        maxx = self.Q_a[state, id]
                else:
                    if (self.Q_b[state, id] > maxx):
                        chosen = opt_neighbors[i][1]
                        maxx = self.Q_b[state, id]

            '''or self.q_b[state, int(self.drone.identifier)]'''
            if (self.Q_a[state, int(self.drone.identifier)] > maxx):
                return None
        else:
            r = random.randint(0, len(opt_neighbors))
            if (r == len(opt_neighbors)):
                return None
            else:
                chosen = opt_neighbors[r][1]
        return chosen

