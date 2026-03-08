from ga.selection.SelectionMethod import SelectionMethod
from ga.mutation import Mutation

class SingleEliteTournamentSelection(SelectionMethod):
    """
    Selection Algorithm that mutates the hardware of every circuit that is not the current best circuit
    """
    def __init__(self, mutation: Mutation, logger, rand):
        super().__init__(logger, rand)
        self._mutation = mutation

    def __call__(self, circuits):
        circuits = sorted(circuits, key=lambda c: c.get_fitness(), reverse=True)

        best = circuits[0]
        self.protected = set([best])
        self._logger.info(f"{best} is current BEST")

        self._mutation(circuits, set(circuits[1:]))
        return circuits
