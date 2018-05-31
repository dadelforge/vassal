import vassal
import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


if __name__ == '__main__':
    n = 100
    t = np.arange(100)
    ts = np.sin(t) + np.random.rand(n)
    ssa = vassal.ssa(ts)
    ssa.decompose()
    fig = plt.figure()
    ax = fig.gca()
    ssa.plot('paired')
    plt.show()