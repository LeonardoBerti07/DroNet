import numpy as np
import multiprocessing
from itertools import chain
from src.simulation.simulator import Simulator
from src.utilities.policies import *

drones = [5]
alphas = [0.5]
gammas = [0.5]
divs = [1000]
epsilons = [15, 20, 25]
optimistic_values = [2, 1, 10]
c_values = [100, 1000]

prova = np.load("prova.npy")
print(prova[:10])

def multi_simulation(drone):
    my_result = []
    for value in epsilons:
        for alpha in alphas:
            for gamma in gammas:
                for div in divs:
                    sum = 0
                    sim = Simulator(drone, alpha, gamma, div, 2, -2, Epsilon(value))
                    sim.run()
                    # we compute the sum of the ratio to choose the best tuple of hyperparameters considering all the possible num of drones
                    sum += len(sim.metrics.drones_packets_to_depot) / sim.metrics.all_data_packets_in_simulation
                    sim.close()
                    my_result.append((alpha, gamma, div, value, sum, drone))

    return my_result


if __name__ == "__main__":
    print("")
    #pool = multiprocessing.Pool(4)
    #results = pool.map(multi_simulation, range(5, 35, 5))
    #results = list(map(tuple, chain.from_iterable(results)))
    #np.save("prova.npy", np.array(results))