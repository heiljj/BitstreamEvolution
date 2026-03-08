from typing import TYPE_CHECKING, List
from logging import Logger
import math

from ga.selection.SelectionMethod import SelectionMethod
from ga.selection.ClassicTournamentSelection import ClassicTournamentSelection
from ga.selection.FitnessProportionalSelection import FitnessProportionalSelection
from ga.selection.FractionalEliteTournament import FractionalEliteTournament
from ga.selection.MapElitesSelection import MapElitesSelection
from ga.selection.RankProportionalSelection import RankProportionalSelection
from ga.selection.SingleEliteTournamentSelection import SingleEliteTournamentSelection

from ga.crossover import crossover_fac
from ga.mutation import mutation_fac
from ga.mixins import Mixin, mixin_fac

from Config import Config

if TYPE_CHECKING:
    import numpy as np
    from CircuitPopulation import CircuitPopulation

class MixinSelection(SelectionMethod):
    """Wrapper around SelectionMethod to run Mixins before and after selection."""
    def __init__(self, before: List[Mixin], selection: SelectionMethod, after: List[Mixin]):
        self._before = before
        self._selection = selection
        self._after = after

    @property
    def protected(self):
        return self._selection.protected

    def __call__(self, circuits):
        circuits = sorted(circuits, key=lambda c : c.get_fitness(), reverse=True)
        for mixin in self._before:
            mixin(circuits, self)
            circuits = sorted(circuits, key=lambda c : c.get_fitness(), reverse=True)

        self._selection(circuits)
        circuits = sorted(circuits, key=lambda c : c.get_fitness(), reverse=True)

        for mixin in self._after:
            mixin(circuits, self)
            circuits = sorted(circuits, key=lambda c : c.get_fitness(), reverse=True)

        return circuits

def selection_fac(population: "CircuitPopulation", config: Config, logger: Logger, rand: "np.random.Generator") -> SelectionMethod:
    crossover_partial = crossover_fac(population, config, logger, rand)
    mutation_partial = mutation_fac(config, logger, rand)
    n_elites = int(math.ceil(config.get_elitism_fraction() * config.get_population_size()))

    match config.get_selection_type():
        case "SINGLE_ELITE":
            selection = SingleEliteTournamentSelection(mutation_partial(), logger, rand)
        case "FRAC_ELITE":
            selection = FractionalEliteTournament(crossover_partial(), mutation_partial(), n_elites, logger, rand)
        case "CLASSIC_TOURN":
            selection = ClassicTournamentSelection(crossover_partial(), mutation_partial(), logger, rand)
        case "FIT_PROP_SEL":
            selection = FitnessProportionalSelection(crossover_partial(), mutation_partial(), n_elites, logger, rand)
        case "RANK_PROP_SEL":
            selection = RankProportionalSelection(crossover_partial(), mutation_partial(), n_elites, logger, rand)
        case "MAP_ELITES":
            selection = MapElitesSelection(config.get_map_elites_dimension(), mutation_partial(), logger, rand)
        case _:
            logger.error("Invalid Selection method in config.ini. Exiting...")
            exit()

    before_mixins, after_mixins = mixin_fac(config, logger, rand)
    return MixinSelection(before_mixins, selection, after_mixins)
