#!/usr/bin/env python3
"""Tiny seeded experiment for `just demo-cpu`: does training-label noise hurt a logistic model?

Numpy only, under a second per seed. It exists to exercise the lab's tools, not to find anything new.
"""
import argparse

import numpy as np

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, required=True)
p.add_argument("--noise", type=float, default=0.2)
args = p.parse_args()

rng = np.random.default_rng(args.seed)
centres = rng.normal(size=(3, 8)) * 1.5


def sample(n):
    y = rng.integers(0, 3, n)
    return centres[y] + rng.normal(size=(n, 8)), y


def accuracy(w, x, y):
    return float((np.argmax(x @ w[:-1] + w[-1], axis=1) == y).mean())


x, y = sample(600)
xt, yt = sample(2000)
noisy = y.copy()
flip = rng.random(len(y)) < args.noise
noisy[flip] = (y[flip] + rng.integers(1, 3, flip.sum())) % 3
onehot = np.eye(3)[noisy]
w = np.zeros((9, 3))
for _ in range(300):
    logits = x @ w[:-1] + w[-1]
    probs = np.exp(logits - logits.max(axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    err = probs - onehot
    w[:-1] -= 0.1 * x.T @ err / len(x)
    w[-1] -= 0.1 * err.mean(axis=0)
print(f"seed {args.seed} noise {args.noise} test_accuracy {accuracy(w, xt, yt):.4f}")
