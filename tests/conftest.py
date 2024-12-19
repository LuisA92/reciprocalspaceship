import re
from os import listdir
from os.path import abspath, dirname, join

import gemmi
import numpy as np
import pytest

import reciprocalspaceship as rs


def load_dataset(datapath, as_gemmi=False):
    """
    Load dataset at given datapath. Datapath is expected to be a list of
    directories to follow.
    """
    inFN = abspath(join(dirname(__file__), *datapath))
    if as_gemmi:
        return gemmi.read_mtz_file(inFN)
    else:
        return rs.read_mtz(inFN)


@pytest.fixture
def data_merged():
    """
    Load HEWL diffraction data from APS 24-ID-C
    """
    datapath = ["data", "data_merged.mtz"]
    return load_dataset(datapath)


@pytest.fixture
def data_unmerged():
    """
    Load HEWL diffraction data from APS 24-ID-C
    """
    datapath = ["data", "data_unmerged.mtz"]
    return load_dataset(datapath)


@pytest.fixture
def hkls(data_merged):
    """
    Return all Miller indices with H, K, L values between [-5, 5]
    """
    return data_merged.hkls


@pytest.fixture
def dataset_hkl(data_merged):
    """
    Build DataSet for testing containing only Miller indices
    """
    H = data_merged.hkls
    dataset = rs.DataSet({"H": H[:, 0], "K": H[:, 1], "L": H[:, 2]})
    dataset.set_index(["H", "K", "L"], inplace=True)
    return dataset


@pytest.fixture
def hkls_unmerged(data_unmerged):
    """
    Return all Miller indices with H, K, L values between [-5, 5]
    """
    return data_unmerged.hkls


@pytest.fixture
def dataset_hkl_unmerged(data_unmerged):
    """
    Build DataSet for testing containing only Miller indices
    """
    H = data_unmerged.hkls
    dataset = rs.DataSet({"H": H[:, 0], "K": H[:, 1], "L": H[:, 2]})
    dataset.set_index(["H", "K", "L"], inplace=True)
    return dataset


@pytest.fixture(
    params=[
        ["data", "data_merged.mtz"],
        ["data", "data_unmerged.mtz"],
    ]
)
def data_hewl(request):
    """Yields DataSet objects for merged and unmerged MTZ files"""
    return load_dataset(request.param)


@pytest.fixture
def data_gemmi():
    """
    Load HEWL diffraction data from APS 24-ID-C as gemmi.Mtz
    """
    datapath = ["data", "fmodel", "9LYZ.mtz"]
    return load_dataset(datapath, as_gemmi=True)


@pytest.fixture
def data_fmodel():
    """
    Load fmodel results for 9LYZ.mtz
    """
    datapath = ["data", "fmodel", "9LYZ.mtz"]
    return load_dataset(datapath)


@pytest.fixture
def data_fmodel_P1():
    """
    Load fmodel results for 9LYZ.mtz
    """
    datapath = ["data", "fmodel", "9LYZ_p1.mtz"]
    return load_dataset(datapath)


def get_mtz_by_spacegroup():
    """
    Get absolute paths to MTZ files generated by phenix.fmodel for
    testing crystallographic symmetry operations.
    """
    datadir = abspath(join(dirname(__file__) + "/data/fmodel/"))
    files = [
        join(datadir, i) for i in listdir(datadir) if re.match(r".*(?<!_p1).mtz$", i)
    ]
    return files


@pytest.fixture(params=get_mtz_by_spacegroup())
def mtz_by_spacegroup(request):
    """Yields paths to MTZ files for each crystallographic spacegroup"""
    return request.param


integer_dtypes = [
    (rs.HKLIndexDtype, "HKL"),
    (rs.MTZIntDtype, "MTZInt"),
    (rs.BatchDtype, "Batch"),
    (rs.M_IsymDtype, "M/ISYM"),
]

float_dtypes = [
    (rs.IntensityDtype, "Intensity"),
    (rs.StructureFactorAmplitudeDtype, "SFAmplitude"),
    (rs.AnomalousDifferenceDtype, "AnomalousDifference"),
    (rs.StandardDeviationDtype, "Stddev"),
    (rs.FriedelStructureFactorAmplitudeDtype, "FriedelSFAmplitude"),
    (rs.StandardDeviationFriedelSFDtype, "StddevFriedelSF"),
    (rs.FriedelIntensityDtype, "FriedelIntensity"),
    (rs.StandardDeviationFriedelIDtype, "StddevFriedelI"),
    (rs.NormalizedStructureFactorAmplitudeDtype, "NormalizedSFAmplitude"),
    (rs.PhaseDtype, "Phase"),
    (rs.WeightDtype, "Weight"),
    (rs.HendricksonLattmanDtype, "HendricksonLattman"),
    (rs.MTZRealDtype, "MTZReal"),
]


@pytest.fixture(params=integer_dtypes)
def dtype_ints(request):
    return request.param


@pytest.fixture(params=float_dtypes)
def dtype_floats(request):
    return request.param


@pytest.fixture(params=integer_dtypes + float_dtypes)
def dtype_all(request):
    return request.param
