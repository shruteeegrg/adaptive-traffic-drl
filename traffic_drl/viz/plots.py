"""Plotting from saved training logs (CSV written by traffic_drl.agent.training)."""

import csv

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt  # noqa: E402


def plot_reward_curve(log_path: str, out_path: str, window: int = 5) -> str:
    """Plot per-episode reward (and its moving average) from a training log."""
    episodes, rewards = [], []
    with open(log_path) as f:
        for row in csv.DictReader(f):
            episodes.append(int(row["episode"]))
            rewards.append(float(row["reward"]))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(episodes, rewards, alpha=0.4, label="episode reward")
    if len(rewards) >= window:
        avg = [sum(rewards[i - window + 1:i + 1]) / window for i in range(window - 1, len(rewards))]
        ax.plot(episodes[window - 1:], avg, label=f"{window}-episode mean")
    ax.set_xlabel("episode")
    ax.set_ylabel("accumulated reward")
    ax.set_title("Training reward curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
