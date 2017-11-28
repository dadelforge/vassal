"""Base class for SSA objects

"""

import abc
import numpy as np
import pandas as pd
# Get svd algorithm from numpy scipy and sklearn
from numpy.linalg import svd as nplapack
from scipy.linalg import svd as splapack
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import svds as sparpack
from sklearn.utils.extmath import randomized_svd
# svd_flip is used to solve sign ambiguities in svd results
from sklearn.utils.extmath import svd_flip

from dtypes import (
    is_1darray_like,
    is_valid_group_dict,
    nested2d_to_flatlist,
    arraylike_to_nparray)


class BadCallError(ValueError):
    """Raised when a method is called before a dependent method."""
    pass


class BaseSSA(object):
    """Base class of SSA object
    
    BaseSSA is a base class for SSA objects. When initiated, BaseSSA map the svd 
    method selected by the user to the decomposition method.
    
    Existing SVD algorithm in python are wrapped to this base class to ensure
    consisency in the outputs generated by the algoritm: Singular vectors are 
    assign to the object as np.matrix type while singular values are 1d 
    np.array.
    
    Common methods to any SSA derived class are implemented here except plot
    methods that are defined in plot.py
    
    """

    __metaclass__ = abc.ABCMeta

    __valid_types = ['pdseries', 'nparray']
    __default_groups = ['ssa_original', 'ssa_reconstruction', 'ssa_residuals']

    def __init__(self, ts, svdmethod, usetype):
        """Base class init method
        """

        # reference attributes

        self._tsindex = None  # pandas index of time series
        self._tsname = None  # pandas series name
        self._usergroups = None  # user defined groups for reconstruction

        self._grpmatrixdict = None  # dictionary to store reconstructed matrix

        ## reference singular value decomposition results

        # 0: Unitary matrix having left singular vectors as columns
        # 1: Singular values
        # 2: Unitary matrix having right singular vectors as rows
        self.svd = [None, None, None]

        # check if usetype is ok

        if usetype not in self.__valid_types:
            raise ValueError('usetype in one of: {}.'.format(
                self.__valid_types.join(', ')))

        # check if time series is one dimensional

        if not is_1darray_like(ts):
            raise TypeError('Arguments \'ts\' should be 1 dimensional.')

        # check if time series is type pd.Series. If so, store attributes.

        if isinstance(ts, pd.Series):
            self._tsindex = ts.index
            self._tsname = ts.name

        if self._tsindex is None and usetype == 'pdseries':
            self._tsindex = range(len(ts))

        # check if time series is real

        tsarr = arraylike_to_nparray(ts)

        if not np.isrealobj(tsarr):
            raise TypeError('Times series elements should be real numbers.')

        # store attributes

        self.ts = tsarr  # time series values
        self.usetype = usetype  # type to use when requesting data
        self._n_ts = len(ts)  # length

        # map the user selected svd method to self.decompose

        self.decompose = self._SVD_METHODS_MAP[svdmethod]

    def __getitem__(self, item):

        grpkeys = self.groups.keys()

        if not isinstance(item, str):

            raise TypeError('Item index should be type str.')

        if item in self._usergroups.keys():

            ts = self._getseries(item)

        elif item == 'ssa_original':

            ts = self.ts

        elif item == 'ssa_reconstruction':

            # Get number of components

            n = self._n_components

            # Reconstruct all the components

            ts = self._reconstruct_group(range(n))


        elif item == 'ssa_residuals':

            # Get residuals components indexes

            residx = self.groups['ssa_residuals']

            # Reconstruct residual components

            ts = self._reconstruct_group(residx)

        else:

            # item is not in the group names
            raise IndexError('Unknown group name \'{}\'.'.format(item))

        return self._format_output_ts(ts)

    # --------------------------------------------------------------------------
    # Properties

    @property
    def groups(self):
        """Retrurn the available group names.
        
        If no grouping was done using self.reconstruct method, group names
        are limited to 'original' and 'ssa_reconstruction'.
        
        If grouping was done using self.reconstruct method, groups returns
        the additional user defined group names and 'ssa_residuals'.
        
        Examples
        --------
        
        >>> ssaobject = BasicSSA(ts=np.random.randint(size=10))
        >>> print ssaobject.groups
        
        
        Notes
        -----
        
        Any group name returned by self.groups is a name that could be used to 
        retrieve a component with brackets (ie calling self.__getitem__ method):
        
        >>> ssaobject['groupname'] # doctest: +SKIP
        
        """

        n = self._n_components

        if self._usergroups:

            # Get user defined group names

            usernames = self._usergroups.keys()

            # Mix default names with user defined group names

            allnames = self.__default_groups[:2] + usernames + \
                       [self.__default_groups[-1]]

            # Get user defined grouped indexes of singular values

            useridx = self._usergroups.values()

            # Flatten user selected indexes and build a set

            flat_useridx = set(nested2d_to_flatlist(useridx))

            # Define residuals as components that are not in user set of idx

            residualidx = [i for i in range(n) if i not in flat_useridx]

            allvals = [None, range(n)] + useridx + [residualidx]

        else:
            allnames = self.__default_groups[:2]
            allvals = [None, range(n)]

        groups = dict(zip(allnames, allvals))

        return groups

    @property
    def usergroups(self):
        """Return user defined groups"""
        return self._usergroups

    @property
    def _n_components(self):
        """Returns the number of singular values"""
        return len(self.svd[1])

    @property
    def _SVD_METHODS_MAP(self):
        """Map user-selected svd method to the proper wrapper
        """
        svdmap = {
            'nplapack': self._nplapack_wrapper,
            'splapack': self._splapack_wrapper,
            'sparpack': self._sparpack_wrapper,
            'skrandom': self._skrandom_wrapper
        }
        return svdmap

    # --------------------------------------------------------------------------
    # Abstract methods

    # Abstract methods are used to ensure that they are implemented in the
    # derived class.

    @abc.abstractmethod
    def _embedseries(self):
        """Time Series Embedding abstract method"""
        pass

    @abc.abstractmethod
    def _reconstruct_group(self, grpidx):
        """Group definition abstract method"""
        pass

    # --------------------------------------------------------------------------
    # Public methods

    def reconstruct(self, groups=None, append=False, overwrite=False):
        """Reconstruct components based on eigentriples indexes. 
        
        Define user groups for the signal reconstruction.

        Parameters
        ----------
        groups : dict
            Dictionnary of user defined groups for reconstruction. Keys 
            represents group names and values are index of eigentriples to use
            for the reconstruction. 
        append : bool, optional
            If append is True, 'groups' are appended to existing user groups.
            If False, 'groups' as the new user groups and previous ones are 
            dropped. Default is False.
        overwrite : bool, optional
            If overwrite is True, if two user groups have the same group names,
            the new group will overwrite the previous one. If False, a 
            ValueError is raised in case of name conflict. 

        Returns
        -------
        None

        """

        # check if self.decompose was done

        if any(item is None for item in self.svd):
            raise BadCallError('reconstruct method cannot be called before '
                               'decompose method.')

        # check groups

        if not isinstance(groups, dict):
            raise TypeError(
                'Argrument \'groups\' should be type dict, not {}.'.format(
                    type(groups)))

        if not is_valid_group_dict(groups):
            raise ValueError(
                'Invalid group dict. Keys should be type str and values type '
                'int or list of int.')

        # check indexes
        # TODO



        # save usergroups if not defined or if append is False

        if self._usergroups is None or not append:

            self._usergroups = groups

        # deal with previous groups if already defined

        else:

            oldgrp = self._usergroups
            newgrp = groups

            common_names = [name for name in newgrp if name in oldgrp]

            if common_names and not overwrite:

                # Raise overwrite error if overwrite is False

                raise ValueError('Group keys cannot be overwritten with '
                                 'overwrite parameters set to False.')

            else:

                # add grpname and indexes to usergroups

                for key, values in newgrp:
                    self._usergroups[key] = values

    # --------------------------------------------------------------------------
    # Private methods

    def _getseries(self, grpkey):
        """Get reconstructed series from grpkey"""

        # retrieve component as 1d np.array

        grpidx = self.groups[grpkey]

        ts = self._reconstruct_group(grpidx)

        return self._format_output_ts(ts)

    def _format_output_ts(self, ts):

        # if usetype == pdseries, conversion to pd.Series type

        if self.usetype == 'pdseries':
            ts = pd.Series(ts, name=self._tsname, index=self._tsindex)

        return ts

    # --------------------------------------------------------------------------
    # Wrappers to SVD solvers

    def _nplapack_wrapper(self, full_matrices=True):
        """Wrapper for numpy.linalg.svd
               
        Apply SVD to the embedding matrix of shape (`M`, `N`) using the 
        `numpy.linalg.svd`_ algorithm based on LAPACK implementation of SVD. 
        
        Parameters
        ----------
        
        full_matrices : bool, optional
            If True (default), `u` and `v` have the shapes (`M`, `M`) and
            (`N`, `N`), respectively.  Otherwise, the shapes are (`M`, `K`)
            and (`K`, `N`), respectively, where `K` = min(`M`, `N`).
            
        See Also
        --------
        
        .. _`numpy.linalg.svd`:
           https://docs.scipy.org/doc/numpy-1.11.0/reference/generated/numpy.linalg.svd.html
            
        """

        # Matrix to be decomposed

        x = self._embedseries()

        # Apply decomposition

        u, s, v = nplapack(x, full_matrices=full_matrices, compute_uv=True)

        # saving svd

        self.svd = [np.matrix(u), s, np.matrix(v)]

        return self.svd

    def _splapack_wrapper(self, full_matrices=True, check_finite=False,
                          lapack_driver='gesdd'):
        """Wrapper for scipy.linalg.svd
               
        Apply SVD to the embedding matrix of shape (`M`, `N`) using the 
        `scipy.linalg.svd`_ algorithm based on LAPACK implementation of SVD. 
        
        Parameters
        ----------
        full_matrices : bool, optional
            If True (default), `U` and `Vh` are of shape ``(M, M)``, ``(N, N)``.
            If False, the shapes are ``(M, K)`` and ``(K, N)``, where
            ``K = min(M, N)``.
        check_finite : bool, optional
            Whether to check that the input matrix contains only finite numbers.
            Disabling may give a performance gain, but may result in problems
            (crashes, non-termination) if the inputs do contain infinities or NaNs.
        lapack_driver : {'gesdd', 'gesvd'}, optional
            Whether to use the more efficient divide-and-conquer approach
            (``'gesdd'``) or general rectangular approach (``'gesvd'``)
            to compute the SVD. MATLAB and Octave use the ``'gesvd'`` approach.
            Default is ``'gesdd'``.

        See Also
        --------
        
        .. _`scipy.linalg.svd`:
           https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.svd.html
            

        """
        # Matrix to be decomposed

        x = self._embedseries()

        # Decomposition

        u, s, v = splapack(x, full_matrices=full_matrices,
                           compute_uv=True,
                           overwrite_a=True,
                           check_finite=check_finite,
                           lapack_driver=lapack_driver)

        self.svd = [np.matrix(u), s, np.matrix(v)]

        return self.svd

    def _sparpack_wrapper(self, k=None, ncv=None, tol=0, v0=None, maxiter=None):
        """Wrapper for scipy.sparse.linalg.svds

        Apply Singular Value Decomposition to the embedding matrix of shape 
        (`M`, `N`) using the `scipy.sparse.linalg.svds`_ algorithm. 

        Parameters
        ----------


        See Also
        --------
        
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.svd.html

        """
        # Matrix to be decomposed

        x = csc_matrix(self._embedseries())

        # Default k value is full svd

        if k is None:
            k = min(x.shape) - 1

        u, s, v = sparpack(x, k=k, ncv=ncv, tol=tol, which='LM', v0=v0,
                           maxiter=maxiter, return_singular_vectors=True)

        # with this implementation vectors needs to be flipped to match lapack
        # other format and sign ambiguities have to be solved to force
        # deterministic output with svd_flip

        u, v = svd_flip(u[:, ::-1], v[::-1, :])

        self.svd = [np.matrix(u), s[::-1], np.matrix(v)]

        return self.svd

    def _skrandom_wrapper(self, k=None, n_oversamples=10, n_iter='auto',
                          power_iteration_normalizer='auto', random_state=None):
        """Wrapper to sklearn.utils.extmath.randomized_svd
        
        Apply Singular Value Decomposition to the embedding matrix of shape 
        (`M`, `N`) using the `sklearn.utils.extmath.randomized_svd`_ algorithm. 
            
        Parameters
        ----------
        
        k : int
            Number of singular values and vectors to extract.
        n_oversamples : int (default is 10)
            Additional number of random vectors to sample the range of M so as
            to ensure proper conditioning. The total number of random vectors
            used to find the range of M is n_components + n_oversamples. Smaller
            number can improve speed but can negatively impact the quality of
            approximation of singular vectors and singular values.
        n_iter : int or 'auto' (default is 'auto')
            Number of power iterations. It can be used to deal with very noisy
            problems. When 'auto', it is set to 4, unless `n_components` is small
            (< .1 * min(X.shape)) `n_iter` in which case is set to 7.
            This improves precision with few components.
            .. versionchanged:: 0.18
        power_iteration_normalizer : 'auto' (default), 'QR', 'LU', 'none'
            Whether the power iterations are normalized with step-by-step
            QR factorization (the slowest but most accurate), 'none'
            (the fastest but numerically unstable when `n_iter` is large, e.g.
            typically 5 or larger), or 'LU' factorization (numerically stable
            but can lose slightly in accuracy). The 'auto' mode applies no
            normalization if `n_iter`<=2 and switches to LU otherwise.
            .. versionadded:: 0.18
        random_state : int, RandomState instance or None, optional (default=None)
            The seed of the pseudo random number generator to use when shuffling
            the data.  If int, random_state is the seed used by the random number
            generator; If RandomState instance, random_state is the random number
            generator; If None, the random number generator is the RandomState
            instance used by `np.random`.
            
        See Also
        -------
        
        *  .. _`sklearn.utils.extmath.randomized_svd`:
            https://github.com/scikit-learn/scikit-learn/blob/439bf1ac896aacafe90177bc28bf036cc8e8e4d9/sklearn/utils/extmath.py#L228
            
        * .. _`sklearn.decomposition.TruncatedSVD`:
            http://scikit-learn.org/stable/modules/generated/sklearn.decomposition.TruncatedSVD.html
            

        """

        # Matrix to be decomposed

        x = csc_matrix(self._embedseries())

        # if k is None get the maximum

        if k is None:
            k = min(x.shape) - 1

        if random_state is None:
            random_state = np.random.RandomState()

        # Sklearn randomized svd decomposition

        u, s, v = randomized_svd(x, n_components=k, n_oversamples=n_oversamples,
                                 n_iter=n_iter,
                                 power_iteration_normalizer=power_iteration_normalizer,
                                 transpose=False, flip_sign=True,
                                 random_state=random_state)

        # store output

        self.svd = [np.matrix(u), s, np.matrix(v)]

        return self.svd


if __name__ == '__main__':
    from vassal.ssa import BasicSSA
    import numpy as np

    np.random.seed(0)
    s = np.random.randint(low=0, high=10, size=200)

    npssa = BasicSSA(s, svdmethod='nplapack')
    spssa = BasicSSA(s, svdmethod='splapack')
    sp2ssa = BasicSSA(s, svdmethod='sparpack')
    skssa = BasicSSA(s, svdmethod='skrandom')
    u1, s1, v1 = npssa.decompose()
    u2, s2, v2 = spssa.decompose()
    u3, s3, v3 = sp2ssa.decompose()
    u4, s4, v4 = skssa.decompose()
    print np.allclose(s1, s2)
    print np.allclose(s2[:-1], s3)
    print np.allclose(s3, s4)

    groups = {
        'trend': 0,
        'season': [1, 2]
    }
    npssa.reconstruct(groups)
    print npssa['trend'].describe()
    print npssa['season'].describe()