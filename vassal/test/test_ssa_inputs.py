import vassal
import unittest
import numpy as np
import pandas as pd


class TestSSAIsFinite(unittest.TestCase):
    def setUp(self):
        np.random.seed(0)
        npts = np.random.rand(100)
        self.npts = npts
        self.pdts = pd.Series(npts)

    def test_npnan(self):
        x = self.npts.copy()
        x[0] = np.nan
        with self.assertRaises(ValueError):
            vassal.ssa(x)

    def test_npinf(self):
        x = self.npts.copy()
        x[0] = np.inf
        with self.assertRaises(ValueError):
            vassal.ssa(x)

    def test_pdnan(self):
        x = self.pdts.copy()
        x[0] = np.nan
        with self.assertRaises(ValueError):
            vassal.ssa(x)

    def test_pdinf(self):
        x = self.pdts.copy()
        x[0] = np.inf
        with self.assertRaises(ValueError):
            vassal.ssa(x)


if __name__ == '__main__':
    unittest.main()
