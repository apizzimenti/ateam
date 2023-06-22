
import numpy as np
import pandas as pd
from functools import reduce

from schedules import constant
from accepts import always
from distributions import uniform

class Model:
    def __init__(self): pass
    def proposal(self): pass
    def accept(self): pass
    def initial(self): pass


class SwendsonWang(Model):
    def __init__(self, temperature=constant(0.7), accept=always(), testing=False):
        """
        Initializes a Swendson-Wang evolution on the Potts model.

        Args:
            temperature (Callable): A function taking an integer argument which
                returns a real-valued temperature. Defaults to the constant
                schedule.
            accept (Callable): A function which takes a Chain as input and returns
                a boolean.
        """
        self.temperature = temperature
        self.accept = accept
        self.testing = testing


    def proposal(self, chain):
        """
        Proposal scheme for the Swendson-Wang evolution on the Potts model. 

        Args:
            chain (Chain): Chain object which contains all the information we
                need.

        Returns:
            A proposed state.
        """
        lattice, state = chain.lattice, chain.state

        # First, create a matrix that includes/excludes the appropriate edges;
        # we scan through them, and "remove" any edges that have no effect.
        M = len(lattice.structure[1])
        included = lattice.field(np.zeros((M, M), dtype=int))

        for edge in lattice.structure[1]:
            u, v = edge.coordinates
            
            # We have three cases:
            #
            #   1. if the spins on u and v are different, we ignore the edge.
            #   2. if the spins on u and v are the same, we
            #       a. include the edge with probability 1-e^beta,
            #       b. ignore the edge with probability e^beta.

            # Case 1.
            if state[u.index] != state[v.index]:
                edge.spin = 0
                continue
            else:
                # Set the probability that an edge is included, and uniformly
                # randomly select a value in [0,1] to determine whether the edge
                # is included.
                p = 1-(np.exp(self.temperature(chain.step)))
                q = np.random.uniform()

                # Case 2(a).
                if q < p:
                    # Testing!
                    if self.testing:
                        print(f"included edge ({u},{v}) with probability {q}<{p}")
                    included[edge.index, edge.index] = 1
                    edge.spin = 1
                
                # Case 2(b).
                else:
                    edge.spin = 0

        # Now that we know which edges we're ignoring, we can multiply the two
        # matrices together!
        boundary = np.matmul(lattice.boundary, included)

        # If we're testing, write the matrices to file and indicate which edges
        # are ignored.
        if self.testing:
            pd.DataFrame(state).to_csv(f"./output/matrices/state-{chain.step}.csv", index=False)
            pd.DataFrame(boundary).to_csv(f"./output/matrices/operator-{chain.step}.csv", index=False)

        # Now, let's change the states!
        coboundary = boundary.T
        basis = coboundary.null_space()
        proposed = np.array(reduce(
            np.add, 
            [uniform(0, chain.lattice.field.order)*b for b in basis]
        ))

        if self.testing: print(proposed)

        return proposed

    def _fromNullSpace(chain, boundary):
        """
        Uniformly randomly chooses a solution in the null space of the coboundary
        matrix.

        Args:
            boundary (galois.FieldArray): A matrix over the field specified by
                the lattice.

        Returns:
            A single vector of spins (values over the field specified by the lattice)
            on the vertices.
        """
        # Find a basis for the null space of the coboundary matrix.
        coboundary = boundary.T
        basis = coboundary.null_space()

        return np.array(reduce(
            np.add, 
            [uniform(0, chain.lattice.field.order)*b for b in basis]
        ))

    
    def initial(self, lattice, distribution=uniform):
        """
        Generates a random initial state.

        Args:
            lattice (Lattice): The integer lattice we're experimenting on.
            distribution (Callable): A distribution from which we'll select;
                this distribution must be _discrete_ and take _two integer inputs_
                representing the lower and higher endpoints of the interval over
                the integers.

        Returns:
            A cocycle with initial states.
        """
        vertices = lattice.structure[0]
        cocycle = np.array([
            distribution(0, lattice.field.order) for _ in range(len(vertices))
        ])

        # If we're testing, give all the vertices the same spin. This way, we
        # should ignore *no* edges.
        if self.testing: return lattice.field(np.array([1]*len(vertices)))
        return lattice.field(cocycle.astype(int))