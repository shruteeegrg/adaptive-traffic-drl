"""Fixed-time signal controller: the baseline the DQN is measured against.

Cycles NS-green / EW-green with a constant green duration (default 42 s,
matching the network's own signal plan in intersection.net.xml). It has the
same act() interface as the learning agents, so the same evaluate() loop
and metrics apply -- an apples-to-apples comparison.

act() is called once per env step; a non-switching step advances the
simulation `step_length` seconds, so `green_steps` calls = that many seconds
of green (the yellow clearance is inserted by the environment on the switch).
"""


class FixedTimeAgent:
    def __init__(self, green_steps: int = 42, n_actions: int = 2):
        self.green_steps = green_steps
        self.n_actions = n_actions
        self._phase = 0
        self._count = 0

    def act(self, state=None, greedy: bool = True) -> int:
        if self._count >= self.green_steps:
            self._phase = (self._phase + 1) % self.n_actions
            self._count = 0
        self._count += 1
        return self._phase

    def reset(self) -> None:
        self._phase, self._count = 0, 0
