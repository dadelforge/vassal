import vassal
import unittest
import numpy as np
import pandas as pd


class TestBasicSSA_nplapack(unittest.TestCase):
    """Test if signal reconstruction is correct"""

    def setUp(self):
        np.random.seed(0)
        npts = np.random.rand(100)
        self.ssa_np = vassal.ssa(npts)
        self.ssa_np.decompose()


    def test_nplapack_recomposition(self):
        x = self.ssa_np['ssa_original'].values
        y = self.ssa_np['ssa_reconstruction'].values
        np.testing.assert_allclose(x,y)

class TestBasicSSA_splapack(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)
        npts = np.random.rand(100)
        self.ssa_np = vassal.ssa(npts, svdmethod='splapack')
        self.ssa_np.decompose()


    def test_splapack_recomposition(self):
        x = self.ssa_np['ssa_original'].values
        y = self.ssa_np['ssa_reconstruction'].values
        np.testing.assert_allclose(x,y)

class TestBasicSSA_sparpack(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)
        npts = np.random.rand(100)
        self.ssa_np = vassal.ssa(npts, svdmethod='sparpack')
        self.ssa_np.decompose(k=49) # we cannot set to 50


    def test_sparpack_recomposition(self):
        x = self.ssa_np['ssa_original'].values
        y = self.ssa_np['ssa_reconstruction'].values
        np.testing.assert_allclose(x,y, atol=1e-2)


class TestBasicSSA_skrandom(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)
        npts = np.random.rand(100)
        pdts = pd.Series(npts)
        self.ssa_np = vassal.ssa(npts, svdmethod='skrandom')
        self.ssa_np.decompose(k=50)


    def test_skrandom_recomposition(self):
        x = self.ssa_np['ssa_original'].values
        y = self.ssa_np['ssa_reconstruction'].values
        np.testing.assert_allclose(x,y, atol=1e-2)


if __name__ == '__main__':
    unittest.main()