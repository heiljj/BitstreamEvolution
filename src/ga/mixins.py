from logging import Logger
from typing import Protocol, List, Tuple, TYPE_CHECKING
from Circuit.Circuit import Circuit
from Config import Config
from ga.selection import SelectionMethod

if TYPE_CHECKING:
    import numpy as np

class Mixin(Protocol):
    def __call__(self, circuits: List[Circuit], selection: SelectionMethod): ...

class RandomInjection(Mixin):
    """Completely randomize the lowest few circuits of each generation."""
    def __init__(self, config: Config):
        super().__init__()
        self._amount = int(config.get_random_injection() * config.get_population_size())

    def __call__(self, circuits, selection):
        circuits_to_randomize = circuits[-self._amount:]
        for circuit in circuits_to_randomize:
            if circuit not in selection.protected:
                circuit.randomize_bitstream()

class ChaosInjection(Mixin):
    """
    If progress stalls, perform large mutations on a portion of the population. Ignores the
    top circuit.
    """
    def __init__(self, config: Config, logger: Logger, rand: "np.random.Generator"):
        super().__init__()
        self._rand = rand
        self._top_fitness = 0
        self._generations_without_increase = 0
        self._logger = logger

        self._generation_threshold = 5
        self._amount_circuits = int(0.1 * config.get_population_size())
        self._mutation_chance = config.get_chaos_injection() * config.get_mutation_probability()

    def __call__(self, circuits, selection):
        if (fitness := circuits[0].get_fitness()) > self._top_fitness:
            self._generations_without_increase = 0
            self._top_fitness = fitness

        self._generations_without_increase += 1
        if self._generations_without_increase < self._generation_threshold:
            return

        self._top_fitness = fitness

        self._logger.info("Adding chaos injection")

        non_protected = [circuit for circuit in circuits[10:] if circuit not in selection.protected]
        for circuit in self._rand.choice(non_protected, self._amount_circuits):
            circuit.mutate(chance=self._mutation_chance)

def mixin_fac(config: Config, logger: Logger, rand: "np.random.Generator") -> Tuple[List[Mixin], List[Mixin]]:
    before = []
    after = []

    if config.get_random_injection() > 0:
        after.append(RandomInjection(config))

    if config.get_chaos_injection() > 0:
        after.append(ChaosInjection(config, logger, rand))

    return before, after


