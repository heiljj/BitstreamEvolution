from logging import Logger
from typing import Protocol, List
from Circuit.Circuit import Circuit
from Config import Config

import numpy as np

class DiversityMeasure(Protocol):
    def __call__(self, circuits: List[Circuit]) -> float:
        """Measures and returns diversity of circuits."""

class HammingDistanceDiversity(DiversityMeasure):
    def __init__(self, logger: Logger):
        self._logger = logger

    def __call__(self, circuits):
        running_total = 0
        n = len(circuits)
        num_pairs = n * (n-1) / 2

        self._logger.event(4, "Starting Hamming Distance Calculation")
        bitstreams = [c.get_bitstream() for c in circuits]

        # We now have all the bitstreams, we can do the faster hamming calculation by comparing each bit of them
        # Then we multiply the count of 1s for that bit by the count of 0s for that bit and add it to the running_total
        # Divide that by # of pairs at the end (calculation shown below)
        # TODO do this with numpy
        running_total = 0
        n = len(circuits)
        num_pairs = n * (n-1) / 2
        self._logger.event(4, "HDIST - Entering loop")
        for i in range(len(bitstreams[0])):
            ones_count = 0
            zero_count = 0
            for j in range(n):
                if bitstreams[j][i] == 0:
                    zero_count = zero_count + 1
                else:
                    ones_count = ones_count + 1
            running_total = running_total + ones_count * zero_count

        running_total = running_total / num_pairs
        self._logger.event(4, "HDIST - Final value", running_total)
        return running_total

class CountUniqueDiversity(DiversityMeasure):
    def __init__(self, logger: Logger):
        self._logger = logger

    def __call__(self, circuits):
        """
        Returns the number of unique files in the population

        Returns
        -------
        int
            Number of unique circuits in the population

        """
        bitstreams = np.array([c.get_bitstream() for c in circuits])
        unique = np.unique(bitstreams, axis=0).shape[0]
        self._logger.event(2, "Number of Unique Individuals:", unique)
        return int(unique)

class CountDifferingBitsDiversity(DiversityMeasure):
    def __init__(self, logger: Logger):
        self._logger = logger

    def __call__(self, circuits):
        l = len(circuits)
        sums = np.array([c.get_bitstream() for c in circuits]).sum(axis=0)
        different = (sums != 0) & (sums != l)
        return int(different.sum())

def null_diversity(circuits: List[Circuit]):
    return 0

def diversity_fac(config: Config, logger: Logger) -> DiversityMeasure:
    match config.get_diversity_measure():
        case "HAMMING_DIST":
            return HammingDistanceDiversity(logger)
        case "UNIQUE":
            return CountUniqueDiversity(logger)
        case "DIFFERING_BITS":
            return CountDifferingBitsDiversity(logger)
        case "NONE":
            return null_diversity
        case _:
            logger.error("Invalid diversity method selected.")
            raise Exception("Invalid diversity method selected.")
