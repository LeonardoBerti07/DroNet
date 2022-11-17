from src.routing_algorithms.BASE_routing import BASE_routing


class GeoRouting(BASE_routing):

    def __init__(self, drone, simulator):
        BASE_routing.__init__(self, drone, simulator)

    def relay_selection(self, opt_neighbors):
        """
        This function returns the best relay to send packets.

        @param opt_neighbors: a list of drones
        @return: The best drone to use as relay
        """

        # TODO: Implement your code HERE

        return None
