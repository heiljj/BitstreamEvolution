from logging import Logger
from typing import TYPE_CHECKING

from ga.selection.SelectionMethod import SelectionMethod
from ga.crossover import Crossover
from ga.mutation import Mutation

if TYPE_CHECKING:
    import numpy as np


class FractionalEliteTournament(SelectionMethod):
    """
    Selection algorithm that compares every circuit in the population to a random elite. If circuit has a lower fitness, crossover or mutate the circuit
    """

    def __init__(self, crossover: Crossover, mutation: Mutation, n_elites: int, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._crossover = crossover
        self._mutation = mutation
        self._n_elites = n_elites

    def __call__(self, circuits):
        self._logger.info("Number of Elites: ", str(self._n_elites))
        self._logger.info("Ranked Fitness: ", circuits)

        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)

        # Generate a group of elite Circuits from the
        # n = <self.__n_elites> best performing Circuits.
        elite_group = list(circuits[:self._n_elites])
        self.protected = set(elite_group)
        self._logger.info("Elite Group:", elite_group)

        # For all the Circuits in the CircuitPopulation compare the
        # Circuit against a random elite Circuit from the group
        # generated above. If the Circuit's fitness is less than than
        # the elite's perform crossover (or clone if crossover is
        # disabled) and then mutate the Circuit.
        for ckt in circuits:
            rand_elite = self._rand.choice(elite_group)
            if ckt.get_fitness() <= rand_elite.get_fitness() and ckt not in elite_group:
                # if self.__config.crossover_probability  == 0:
                #     self.__logger.event(3, "Cloning:", rand_elite, " ---> ", ckt)
                #     ckt.replace_hardware_file(rand_elite.get_hardware_filepath)
                # else:
                #     self.__single_point_crossover(rand_elite, ckt)

                if not self._crossover(rand_elite, ckt):
                    self._logger.event(3, "Cloning:", rand_elite, " ---> ", ckt)
                    ckt.copy_from(rand_elite)

        self._mutation(circuits, set(circuits))

        return circuits