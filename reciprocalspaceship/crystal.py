import pandas as pd
import numpy as np
import gemmi
from .utils import canonicalize_phases

class CrystalSeries(pd.Series):
    """
    Representation of a sliced Crystal
    """
    
    @property
    def _constructor(self):
        return CrystalSeries

    @property
    def _constructor_expanddim(self):
        return Crystal
    
class Crystal(pd.DataFrame):
    """
    Representation of a crystal

    Attributes
    ----------
    spacegroup : gemmi.SpaceGroup
        Crystallographic space group containing symmetry operations
    cell : gemmi.UnitCell
        Unit cell constants of crystal (a, b, c, alpha, beta, gamma)
    cache_index_dtypes : Dictionary
        Dictionary of dtypes for columns in Crystal.index. Populated upon
        calls to Crystal.set_index() and depopulated by calls to 
        Crystal.reset_index()
    """

    _metadata = ['spacegroup', 'cell', 'cache_index_dtypes']

    def __init__(self, *args, **kwargs):
        self.spacegroup = kwargs.pop('spacegroup', None)
        self.cell = kwargs.pop('cell', None)
        self.cache_index_dtypes = kwargs.pop('cache_index_dtypes', {})
        super().__init__(*args, **kwargs)
        return
    
    @property
    def _constructor(self):
        def _c(*args, **kwargs):
            return Crystal(*args, **kwargs).__finalize__(self)
        return _c

    @property
    def _constructor_sliced(self):
        return CrystalSeries

    def set_index(self, keys, **kwargs):
        
        # Copy dtypes of keys to cache
        for key in keys:
            self.cache_index_dtypes[key] = self[key].dtype.name

        return super().set_index(keys, **kwargs)

    def reset_index(self, **kwargs):
        
        if kwargs.get("inplace", False):
            super().reset_index(**kwargs)

            # Cast all values to cached dtypes
            if not kwargs.get("drop", False):
                for key in self.cache_index_dtypes.keys():
                    dtype = self.cache_index_dtypes[key]
                    self[key] = self[key].astype(dtype)
                self.cache_index_dtypes = {}
            return
        
        else:
            newdf = super().reset_index(**kwargs)

            # Cast all values to cached dtypes
            if not kwargs.get("drop", False):
                for key in newdf.cache_index_dtypes.keys():
                    dtype = newdf.cache_index_dtypes[key]
                    newdf[key] = newdf[key].astype(dtype)
                newdf.cache_index_dtypes = {}
            return newdf

    def write_mtz(self, mtzfile):
        """
        Write an MTZ reflection file from the reflection data in a Crystal.

        Parameters
        ----------
        mtzfile : str or file
            name of an mtz file or a file object
        """
        from reciprocalspaceship import io
        return io.write_mtz(self, mtzfile)

    def get_phase_keys(self):
        """
        Return column labels associated with phase data

        Returns
        -------
        keys : list of strings
            list of column labels
        """
        keys = []
        for k in self:
            try:
                if self[k].dtype.mtztype == "P":
                    keys.append(k)
            except:
                continue
        return keys

    def apply_symop(self, symop, inplace=False):
        """
        Apply symmetry operation to all reflections in Crystal object. 

        Parameters
        ----------
        symop : gemmi.Op
            Gemmi symmetry operation
        inplace : bool
            Whether to return a new DataFrame or make the change in place
        """
        if not isinstance(symop, gemmi.Op):
            raise ValueError(f"Provided symop is not of type gemmi.Op")
        
        # Apply symop to generate new HKL indices and phase shifts
        hkl = np.vstack(self.index)
        newhkl = hkl.copy()
        phase_shifts  = np.zeros(len(hkl))

        # TODO: This for loop can be removed if gemmi.Op.apply_to_hkl() were vectorized
        for i, h in enumerate(hkl):
            newhkl[i] = symop.apply_to_hkl(h)
            phase_shifts = symop.phase_shift(*h)
        phase_shifts = np.rad2deg(phase_shifts)
            
        if inplace:
            self.reset_index(inplace=True)
            self[['H', 'K', 'L']] = newhkl
            self.set_index(['H', 'K', 'L'], inplace=True)
            F = self
        else:
            F = self.copy().reset_index()
            F[['H', 'K', 'L']] = newhkl
            F.set_index(['H', 'K', 'L'], inplace=True)

        # Shift phases according to symop
        for key in F.get_phase_keys():
            F[key] += phase_shifts
            F[key] = canonicalize_phases(F[key], deg=True)
            
        return F.__finalize__(self)
  
    def _label_centrics(self):
        """
        Label centric reflections in Crystal object. A new column of
        booleans, "CENTRIC", is added to the object.
        """
        self['CENTRIC'] = False
        hkl = np.vstack(self.index)
        for op in self.spacegroup.operations():

            # TODO: This for loop could be removed if op.apply_to_hkl()
            #       were vectorized
            newhkl = hkl.copy()
            for i, h in enumerate(hkl):
                newhkl[i] = op.apply_to_hkl(h)
                
            self['CENTRIC'] = np.all(np.isclose(newhkl, -hkl), 1) | self['CENTRIC']
        return self

    def unmerge_anomalous(self, inplace=False):
        """
        Unmerge Friedel pairs. In the near future, this should probably
        be rolled into a bigger unmerge() function
        """
        self._label_centrics()
        Fplus = self.copy()
        Fminus = self.copy().reset_index()
        Fminus[['H', 'K', 'L']] = -1*Fminus[['H', 'K', 'L']]
        for k in self.get_phase_keys():
            Fminus.loc[~Fminus.CENTRIC, k] = -Fminus.loc[~Fminus.CENTRIC, k]
        Fminus = Fminus.set_index(['H', 'K', 'L'])

        F = Fplus.append(Fminus.loc[Fminus.index.difference(Fplus.index)])
        
        if inplace:
            self._data = F._data
            return self
        else:
            return F.__finalize__(self)
        
    def hkl_to_asu(self, inplace=False):
        """
        Map all HKL indices to the reciprocal space asymmetric unit; return a copy
        This is provisional. Doesn't quite work yet. 
        """
        H = np.vstack(self.index.values).astype(int)
        reflid = np.arange(len(self))

        new_hkl = None
        for op in self.spacegroup.operations():
            #TODO: replace apply_along_axis which is slower than a for loop
            #TODO: refactor this to use apply_symop later
            h = np.apply_along_axis(op.apply_to_hkl, 1, H)
            phase_shift = np.apply_along_axis(lambda x: op.phase_shift(*x), 1, H)
            phase_shift = np.rad2deg(phase_shift)
            new_hkl = pd.concat((new_hkl, pd.DataFrame({
                'H'  : h[:,0], 
                'K'  : h[:,1], 
                'L'  : h[:,2], 
                'PHASE_SHIFT': phase_shift, 
                'ID' : reflid, 
                'FRIEDEL' : False,
            })))

        fminus = new_hkl.copy()
        fminus.loc[:, ['H', 'K', 'L']] = -fminus.loc[:, ['H', 'K', 'L']]
        fminus['FRIEDEL'] = True
        new_hkl = pd.concat((new_hkl, fminus))
        #new_hkl = new_hkl.sort_values(['H', 'K', 'L']).groupby('ID').last()
#Sign sort
        new_hkl[['sH', 'sK', 'sL']] = np.sign(new_hkl.loc[:,['H', 'K', 'L']])
        new_hkl = new_hkl.sort_values(['sH', 'sK', 'sL']).groupby('ID').last()

        if inplace:
            new_crystal = self
        else:
            new_crystal = self.copy()

        new_crystal.reset_index(inplace=True)
        new_crystal.loc[:, ['H', 'K', 'L']] = new_hkl.loc[:, ['H', 'K', 'L']]
        for k in new_crystal.get_phase_keys():
            new_crystal[k] = canonicalize_phases((1. - 2.*new_hkl['FRIEDEL'])*(new_crystal[k] + new_hkl['PHASE_SHIFT']))
        new_crystal.set_index(['H', 'K', 'L'], inplace=True)
        return new_crystal


