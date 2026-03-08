from logging import Logger
from typing import Protocol, List, Set, TYPE_CHECKING
from Config import Config
from Circuit.Circuit import Circuit

if TYPE_CHECKING:
    import numpy as np

class Mutation(Protocol):
    # The inclusion of both all_circuits and circuits_to_mutate allows mutation methods
    # to access information about the fitness of all circuits in the population
    def __call__(self, all_circuits: List[Circuit], circuits_to_mutate: Set[Circuit]):
        """Performs an in place mutation on a list of circuits."""

class SimpleMutation(Mutation):
    def __call__(self, all_circuits, circuits_to_mutate):
        for circuit in circuits_to_mutate:
            circuit.mutate()

class FitnessRankMutation(Mutation):
    """
    Scales mutation chance from 0.5x to 1.5x linearly by fitness rank starting with the
    highest ranked circuits.
    """
    def __init__(self, config: Config):
        self._prob_start = config.get_mutation_probability() / 2

        if config.get_population_size() == 1:
            self._prob_delta = 0
        else:
            self._prob_delta = config.get_mutation_probability() / (config.get_population_size() - 1)

    def __call__(self, all_circuits, circuits_to_mutate):
        for i, circuit, in enumerate(all_circuits):
            if circuit in circuits_to_mutate:
                circuit.mutate(chance=self._prob_start + self._prob_delta * i)

class FitnessProportionalMutation(Mutation):
    """
    Maps circuit fitness range linearly to [0.5x, 1.5x] mutation chance, higher fitness
    circuits are given lower mutation chances.
    """
    def __init__(self, config: Config):
        self._prob = config.get_mutation_probability()
        self._start_prob = self._prob * 1.5

    def __call__(self, all_circuits, circuits_to_mutate):
        highest = all_circuits[0].calculate_fitness()
        lowest = all_circuits[-1].calculate_fitness()

        df = highest - lowest
        dm_df = - self._prob / df

        for circuit in circuits_to_mutate:
            fitness_dif = circuit.calculate_fitness() - lowest
            additional_mutation = fitness_dif * dm_df
            circuit.mutate(chance=self._start_prob + additional_mutation)

class ConvergenceProportionalMutation(Mutation):
    """
    Implements mutation as described by *Adaptive Probabilities of Crossover and Mutation in Genetic Algorithms*.
    Includes modification of using min.
    """
    #TODO still fine tuning this dont use
    def __init__(self, config: Config):
        self._prob = config.get_mutation_probability() * 2
        # Paper uses 0.005, thats pretty high for us
        self._base_prob = config.get_mutation_probability() * 0.5

    def __call__(self, all_circuits, circuits_to_mutate):
        f_bar = sum(circuit.calculate_fitness() for circuit in all_circuits) / len(all_circuits)
        f_max = max(circuit.calculate_fitness() for circuit in all_circuits)

        for circuit in circuits_to_mutate:
            if f_bar == f_max:
                multiplier = 4
            else:
                multiplier = min((f_max - circuit.calculate_fitness()) / (f_max - f_bar), 4)
            print("mutation: ", multiplier)
            circuit.mutate(chance=self._prob * multiplier + self._base_prob)

def mutation_fac(config: Config, logger: Logger, rand: "np.random.Generator"):
    def build():
        match config.get_mutation_type():
            case "SIMPLE":
                return SimpleMutation()
            case "RANK":
                return FitnessRankMutation(config)
            case "PROPORTIONAL":
                return FitnessProportionalMutation(config)
            case "CONVERGENCE":
                return ConvergenceProportionalMutation(config)
            case _:
                logger.error("Invalid mutation type")
                raise Exception("Invalid mutation type")

    return build