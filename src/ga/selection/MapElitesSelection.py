
import math
from logging import Logger
from typing import List, TYPE_CHECKING

from Circuit.Circuit import Circuit
from ga.selection.SelectionMethod import SelectionMethod
from ga.mutation import Mutation

if TYPE_CHECKING:
    import numpy as np

class MapElitesSelection(SelectionMethod):
    """
    Selection Algorithm that is an alternate version of the map elites algorithm from another paper.
    This version of map elites will protect the highest-fitness individual in each "square"
    We're going to have slightly granular squares to make sure that circuits have room to spread out early
    to hopefully promote diversity
    Group size length of 50 means we'll have 21x21 groups
    """
    ELITE_MAP_SCALE_FACTOR = 50
    ELITE_MAP_SCALE_FACTOR = 50
    PULSE_ELITE_MAP_SCALE_FACTOR = 5000
    def __init__(self, elites_dimension: int, mutation: Mutation, logger: Logger, rand: "np.random.Generator"):
        super().__init__(logger, rand)
        self._elites_dimension = elites_dimension
        self._mutation = mutation

    def _generate_map(self, circuits: List[Circuit]) -> List[List[Circuit]]:
        """
        Generates the elite map for this generation based on variance.

        Returns
        -------
        list(list(Circuit))
            A 2D array of circuits categorized based off of shared characteristics
        """
        # If the value is not a circuit (i.e. it is 0) then we know the spot is open to be filled in
        # Go up to 21 since upper bound is 1024
        # Can't do [[0]*21]*21 because this will make all the sub-arrays point to same memory location
        elite_map = [[0] * 21 for _ in range(22)]

        # Evaluate each circuit's fitness and where it falls on the elite map
        # Populate elite map first
        for ckt in circuits:
            row = math.floor(ckt.get_low_value() / self.ELITE_MAP_SCALE_FACTOR)
            col = math.floor(ckt.get_high_value() / self.ELITE_MAP_SCALE_FACTOR)
            if elite_map[row][col] == 0 or ckt.get_fitness() > elite_map[row][col].get_fitness():
                elite_map[row][col] = ckt
        return elite_map

    def _generate_pulse_map(self, circuits: List[Circuit]) -> List[List[Circuit]]:
        """
        Generates the elite map for this generation based on pulse count.

        Returns
        -------
        Circuit[][]
            A 2D array of circuits categorized based off of shared characteristics
        """

        elite_map = []
        for _ in range((150_000 - 1_000) / self.PULSE_ELITE_MAP_SCALE_FACTOR):
            elite_map.append(0)

        for ckt in circuits:
            col = math.floor(ckt.get_mean_frequency() / self.PULSE_ELITE_MAP_SCALE_FACTOR)
            if elite_map[col] == 0 or ckt.get_fitness() > elite_map[col].get_fitness():
                elite_map[col] = ckt
        return elite_map

    # this feels really wrong but probably the best place for it
    def _output_map_file(self, elite_map):
        """
        Writes the map to a file (workspace/maplivedata.log)

        Parameters
        ----------
        elite_map : Circuit[][]
            2D array of circuits that fell into these groupings depending on their characteristics.
        """
        with open("workspace/maplivedata.log", "w+") as liveFile:
            # First line describes granularity/scale factor
            liveFile.write("{}\n".format(str(self.ELITE_MAP_SCALE_FACTOR)))
            # If square is empty, write a "blank" to that line
            if self._elites_dimension() == 1:
                for c in range(len(elite_map)):
                    ckt = elite_map[c]
                    if ckt != 0:
                        liveFile.write("{} {}\n".format(c, ckt.get_fitness()))
            else:
                for r in range(len(elite_map)):
                    sl = elite_map[r]
                    for c in range(len(sl)):
                        ckt = sl[c]
                        to_write = ""
                        if ckt != 0:
                            to_write = str(ckt.get_fitness())
                        liveFile.write("{} {} {}\n".format(r, c, to_write))

    def __call__(self, circuits):
        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)

        if self._elites_dimension == 1:
            elite_map = self._generate_pulse_map(circuits)
            elites = list(filter(lambda x: x != 0, [j for j in elite_map]))
        else:
            elite_map = self._generate_map(circuits)
            elites = list(filter(lambda x: x != 0, [j for sub in elite_map for j in sub]))

        self.protected = elites

        for ckt in circuits:
            # If not an elite, then we will clone and mutate
            if ckt not in elites:
                rand_elite = self._rand.choice(elites)
                ckt.copy_from(rand_elite)

        self._mutation(circuits, set(circuits))
        self._output_map_file(elite_map)

        return circuits
