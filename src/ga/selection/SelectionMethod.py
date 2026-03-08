from abc import ABC
from logging import Logger
from typing import List

import numpy as np

from Circuit.Circuit import Circuit

class SelectionMethod(ABC):
    def __init__(self, logger: Logger, rand: np.random.Generator):
        self._logger = logger
        self._rand = rand
        self.protected = set()

    def __call__(self, circuits: List[Circuit]) -> List[Circuit]:
        """
        Runs a selection algorithm on a group of circuits. May modify
        existing circuits during the process.
        """
