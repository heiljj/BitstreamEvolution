from logging import Logger
from typing import TYPE_CHECKING

from ga.selection.SelectionMethod import SelectionMethod
from ga.crossover import Crossover
from ga.mutation import Mutation

if TYPE_CHECKING:
    import numpy as np

class RankProportionalSelection(SelectionMethod):
    """"
    Selection algorithm that compares every circuit in the population to a random elite (chosen proportionally based on each elite's rank).
    If circuit has a lower fitness, crossover or mutate the circuit
    """

    def __init__(self, crossover: Crossover, mutation: Mutation, n_elites: int, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._crossover = crossover
        self._mutation = mutation
        self._self_n_elites = n_elites

    def __call__(self, circuits):
        self._logger.event(2, "Number of Elites:", self._n_elites)
        self._logger.event(2, "Ranked Fitness:", circuits)

        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)
        # Generate a group of elites from the best n = <self.__n_elites>
        # Circuits. Based on their fitness values, map each Circuit with
        # a probability value (used later for crossover/copying/mutation).
        elites = {}
        rank_sum = sum(range(1, self._n_elites + 1))

        for i in range(self._n_elites):
            # Using (self.__n_elites - i) since highest ranked individual is at self.__circuits[0]
            elites[circuits[i]] = (self._n_elites - i) / rank_sum

        self.protected = set(elites.keys())

        self._logger.event(3, "Elite Group:", elites.keys())
        self._logger.event(3, "Elite Probabilities:", elites.values())

        #self.__logger.event(3, "Elite", rand_elite)

        # For all Circuits in this CircuitPopulation, choose a random
        # elite (based on the associated probabilities calculated above)
        # and compare it to the Circuit. If the Circuit has lower
        # fitness than the elite, perform crossover (with the elite) and
        # mutation on it (or copy the elite's hardware if crossover is
        # disabled).
        elite_prob_sum = sum(elites.values())

        for ckt in circuits:
            if self._n_elites:
                if elite_prob_sum > 0:
                    rand_elite = self._rand.choice(
                        list(elites.keys()),
                        self._n_elites,
                        p=list(elites.values())
                    )[0]
                else:  # If fitness isn't negative, this should never happen
                    rand_elite = self._rand.choice(list(elites.keys()))[0]
            else:
                rand_elite = self._rand.choice(circuits)

            if ckt.get_fitness() <= rand_elite.get_fitness() and ckt != rand_elite and ckt not in elites:
                # NOTE already was commented out
                # if self.__config.get_crossover_probability() == 0:
                #     self.__logger.event(3, "Cloning:", rand_elite, " ---> ", ckt)
                #     ckt.copy_from(rand_elite)
                # else:
                #     self.__single_point_crossover(rand_elite, ckt)
                if not self._crossover(rand_elite, ckt):
                    self._logger.event(3, "Cloning:", rand_elite, " ---> ", ckt)
                    ckt.copy_from(rand_elite)

        self._mutation(circuits, set(circuits) - set(elites.keys()))
        return circuits