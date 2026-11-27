"""A time-limit cut-off is stored as non-terminal only for agents that opt in (dqn.bootstrap_on_timeout)."""
from traffic_drl.agent.dqn_agent import DQNAgent
from traffic_drl.agent.training import bootstrap_done


def test_default_keeps_timeout_terminal():
    agent = DQNAgent(state_dim=2)
    assert bootstrap_done(agent, True, {"truncated": True}) is True


def test_opt_in_bootstraps_through_timeout_only():
    agent = DQNAgent(state_dim=2, bootstrap_on_timeout=True)
    assert bootstrap_done(agent, True, {"truncated": True}) is False
    assert bootstrap_done(agent, True, {"truncated": False}) is True   # network emptied: really terminal
    assert bootstrap_done(agent, False, {"truncated": False}) is False
    assert bootstrap_done(agent, True, {}) is True                     # envs without the flag (toy env)
