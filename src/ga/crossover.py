from logging import Logger
from typing import Protocol, TYPE_CHECKING, Tuple, List

from Circuit.Circuit import Circuit
from Config import Config

if TYPE_CHECKING:
    import numpy as np
    from CircuitPopulation import CircuitPopulation

class Crossover(Protocol):
    def __call__(self, source: Circuit, dest: Circuit) -> bool:
        """Returns whether a crossover was performed."""

class SimpleCrossover(Crossover):
    def __init__(self, config: Config, rand: "np.random.Generator"):
        self._rand = rand
        self._prob = config.get_crossover_probability()
        self._row_bounds = config.get_routing_rows()[0], config.get_routing_rows()[-1]

    def __call__(self, source: Circuit, dest: Circuit) -> bool:
        if self._rand.uniform(0, 1) <= self._prob:
            point = self._rand.integers(*self._row_bounds)
            dest.crossover(source, point)
            return True

        return False

class EachCrossover(Crossover):
    def __init__(self, config: Config, rand: "np.random.Generator"):
        self._rand = rand
        self._prob = config.get_crossover_probability()
        self._row_bounds = config.get_routing_rows()[0], config.get_routing_rows()[-1]

    def __call__(self, source: Circuit, dest: Circuit) -> bool:
        if self._rand.uniform(0, 1) <= self._prob:
            dest.crossover_each(source, self._row_bounds, self._rand)
            return True

        return False

class ConvergenceProportionalCrossover(Crossover):
    """
    Implements crossover as described by *Adaptive Probabilities of Crossover and Mutation in Genetic Algorithms*.
    Modified by adding +1 in denominator to account for closely convergent populations.
    """
    def __init__(self, population: "CircuitPopulation", config: Config, logger: Logger, rand: "np.random.Generator"):
        self._population = population
        self._rand = rand
        self._prob = config.get_crossover_probability()
        # Paper uses 0.005, thats pretty high for us
        self._base_prob = config.get_crossover_probability() * 0.2
        self._row_bounds = config.get_routing_rows()[0], config.get_routing_rows()[-1]


    def __call__(self, source: Circuit, dest: Circuit):
        # TODO don't really like using circuitpop line this
        # current alternative is to pass list of all circuits for each call, but thats also messy since
        # that propagates to all selections also needing to use circuitpop, a lot worse than this
        all_circuits = self._population._circuits
        f_bar = sum(circuit.calculate_fitness() for circuit in all_circuits) / len(all_circuits)
        f_max = max(circuit.calculate_fitness() for circuit in all_circuits)

        if f_bar == f_max:
            multiplier = 4
        else:
            multiplier = min((f_max - source.calculate_fitness()) / (f_max - f_bar), 4)

        chance = self._prob * multiplier + self._base_prob
        print("crossover: ", chance)
        if self._rand.uniform(0, 1) <= chance:
            dest.crossover_each(source, self._row_bounds, self._rand)

def crossover_fac(population: "CircuitPopulation", config: Config, logger: Logger, rand: "np.random.Generator"):
    def build():
        # return ConvergenceProportionalCrossover(population, config, logger, rand)
        return SimpleCrossover(config, rand)

    return build
