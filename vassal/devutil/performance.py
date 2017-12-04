"""
Decorators for performance analysis

"""

import time

class options(object):
    """
    Examples
    --------
    >>> print options.__PRINT_PRECISION__
    3
    
    >>> options.set_precision(5)
    >>> print options.__PRINT_PRECISION__
    5
    
    
    """
    __PRINT_PRECISION__ = 3
    __TIME_UNIT__ = 's' # For unit conversion, not implemented

    @classmethod
    def set_precision(cls, decimals):
        cls.__PRINT_PRECISION__ = decimals



def timerprinter(func):
    """Decorate the function to run it once and print the time.
    
    Parameters
    ----------
    func: callable
        The function to be decorated

    Returns
    -------
        decorated function
        
        
    Examples
    --------
    
    >>> f = lambda: time.sleep(0.5)
    >>> f = timerprinter(f) 
    >>> f()  # doctest:+ELLIPSIS
    Run <lambda> once in: 0.5... s
    
    
    """

    def wrapper(*args, **kwargs):
        before = time.time()
        result = func(*args, **kwargs)
        after = time.time()
        elapsed = round(after - before, options.__PRINT_PRECISION__)
        print 'Run {0.__name__} once in: {1} s'.format(func, elapsed)
        return result

    return wrapper


def ntimerprinter(n):
    """Decorate the function to run it n times and print the time
    
    Parameters
    ----------
    func: callable
        The function to be decorated

    Returns
    -------
        decorated function
        
        
    Examples
    --------
    
    >>> f = lambda: time.sleep(0.2)
    >>> f = ntimerprinter(5)(f)
    >>> f() # doctest:+ELLIPSIS
    Run <lambda> 5 times in: 1... s
    
    """

    def inner(func):

        def wrapper(*args, **kwargs):

            before = time.time()

            for _ in range(n):
                result = func(*args, **kwargs)

            after = time.time()
            elapsed = round(after - before, options.__PRINT_PRECISION__)

            print 'Run {0.__name__} {1} times in: {2} s'.format(func, n,
                                                                    elapsed)
            return result

        return wrapper

    return inner


def timercomputer(func):
    """Decorate the function to run it once and return elapsed time
    
    The time is returned and the function output is disregarded. 
    
    Parameters
    ----------
    func: callable
        The function to be decorated

    Returns
    -------
        time : float
            time in ms
            
    Examples
    --------
    
    >>> f = lambda: time.sleep(0.5)
    >>> f = timercomputer(f)
    >>> f() # doctest: +ELLIPSIS
    0.5...
    
    
    """
    def wrapper(*args, **kwargs):
        before = time.time()
        _ = func(*args, **kwargs)
        after = time.time()
        elapsed = after - before
        return elapsed

    return wrapper


def ntimercomputer(func):
    """Decorate the function to run it once and return elapsed time

    The time is returned and the function output is disregarded. 

    Parameters
    ----------
    func: callable
        The function to be decorated

    Returns
    -------
        time : float
            time elapsed in ms for 1 run. 
    """
    pass


def ntimercomputer(n):
    """
    
    Parameters
    ----------
    func: callable
        The function to be decorated

    Returns
    -------
    timelist : list of float
        list of time elapsed for n run. 
        
    Examples
    --------
    
    >>> f = lambda: time.sleep(0.2)
    >>> f = ntimercomputer(3)(f)
    >>> f() # doctest:+ELLIPSIS
    [0.2..., 0.2..., 0.2...]

    """
    def inner(func):

        def wrapper(*args, **kwargs):

            timelist = []

            for _ in range(n):
                before = time.time()
                result = func(*args, **kwargs)
                after = time.time()
                elapsed = after - before
                timelist.append(elapsed)

            return timelist

        return wrapper

    return inner


if __name__ == '__main__':
    import doctest

    doctest.testmod()
