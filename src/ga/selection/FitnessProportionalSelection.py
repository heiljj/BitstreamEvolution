from typing import TYPE_CHECKING
from logging import Logger

from ga.selection.SelectionMethod import SelectionMethod
from ga.crossover import Crossover
from ga.mutation import Mutation

if TYPE_CHECKING:
    import numpy as np

class FitnessProportionalSelection(SelectionMethod):
    def __init__(self, crossover: Crossover, mutation: Mutation, n_elites: int, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._crossover = crossover
        self._mutation = mutation
        self._n_elites = n_elites
        self._rand = rand

    def __call__(self, circuits):
        """
        Selection algorithm that compares every circuit in the population to a random elite (chosen proportionally based on each elite's fitness).
        If circuit has a lower fitness, crossover or mutate the circuit
        """
        self._logger.event(2, "Number of Elites:", self._n_elites)
        self._logger.event(2, "Ranked Fitness:", circuits)

        # Generate a group of elites from the best n = <self.__n_elites>
        # Circuits. Based on their fitness values, map each Circuit with
        # a probability value (used later for crossover/copying/mutation).
        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)
        elites = circuits[:self._n_elites]
        self.protected = set(elites)
        total_fitness = sum(c.get_fitness() for c in elites)

        if total_fitness:
            elite_chances = {
                c: c.get_fitness() / total_fitness for c in elites
            }
        else:
            elite_chances = {
                c: 1 / self._n_elites for c in circuits[:self._n_elites]
            }

        self._logger.event(2, "Elite Group:", elites)
        self._logger.event(2, "Elite Probabilities:", elite_chances.values())

        # For all Circuits in this CircuitPopulation, choose a random
        # elite (based on the associated probabilities calculated above)
        # and compare it to the Circuit. If the Circuit has lower
        # fitness than the elite, perform crossover (with the elite) and
        # mutation on it (or copy the elite's hardware if crossover is
        # disabled).
        circuits_to_mutate = set()

        for ckt in circuits:
            if self._n_elites:
                if total_fitness >= 0:
                    rand_elite = self._rand.choice(
                        list(elite_chances.keys()),
                        self._n_elites,
                        p=list(elite_chances.values())
                    )[0]
                else:  # If fitness isn't negative, this should never happen
                    rand_elite = self._rand.choice(elites)

            else:
                rand_elite = self._rand.choice(circuits)

            self._logger.event(4, "Elite", rand_elite)

            if ckt.get_fitness() <= rand_elite.get_fitness() and ckt is not rand_elite and ckt not in elites:
                # NOTE this was already commented out
                # if self.__config.get_crossover_probability() == 0:
                # 	self.__logger.event(3, "Cloning:", rand_elite, " ---> ", ckt)
                # 	ckt.copy_from(rand_elite)
                # else:
                # 	self.__single_point_crossover(rand_elite, ckt)
                if not self._crossover(rand_elite, ckt):
                    self._logger.event(4, "Cloning:", rand_elite, " ---> ", ckt)
                    ckt.copy_from(rand_elite)

                circuits_to_mutate.add(ckt)

        self._mutation(circuits, circuits_to_mutate)

        return circuits
