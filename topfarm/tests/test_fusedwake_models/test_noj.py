import pytest

import numpy as np
from topfarm.tests.test_files import tfp
from topfarm._topfarm import TopFarm
from topfarm.cost_models.fused_wake_wrappers import FusedWakeNOJWakeModel
from topfarm.cost_models.utils.aep_calculator import AEPCalculator
from topfarm.cost_models.utils.wind_resource import WindResource
import warnings


@pytest.fixture()
def aep_calc():
    # f, A, k = read_lib(fuga_path + 'LUT/Farms/Horns Rev 1\hornsrev_north_only_pm45.lib')
    f = [1.0, 0.0, 0.0, 0.0]
    A = [9.176929, 9.782334, 9.531809, 9.909545]
    k = [2.392578, 2.447266, 2.412109, 2.591797]
    wr = WindResource(f, A, k, ti=np.zeros_like(f) + .1)
    with warnings.catch_warnings():  # suppress "warning, make sure that this position array is oriented in ndarray([n_wt, 2]) or ndarray([n_wt, 3])"
        warnings.simplefilter("ignore")
        wm = FusedWakeNOJWakeModel(tfp + "wind_farms/3tb.yml")
    return AEPCalculator(wr, wm)


def test_NOJ(aep_calc):
    init_pos = aep_calc.wake_model.windFarm.pos
    with warnings.catch_warnings():  # suppress "warning, make sure that this position array is oriented in ndarray([n_wt, 2]) or ndarray([n_wt, 3])"
        warnings.simplefilter("ignore")
        assert aep_calc(init_pos[:, 0], init_pos[:, 1]) == 18.90684500124578
        assert aep_calc([-500, 0, 500], [0, 0, 0]) == 22.31788007605505


def test_NOJ_Topfarm(aep_calc):
    init_pos = aep_calc.wake_model.windFarm.pos
    with warnings.catch_warnings():  # suppress "warning, make sure that this position array is oriented in ndarray([n_wt, 2]) or ndarray([n_wt, 3])"
        warnings.simplefilter("ignore")
        tf = TopFarm(init_pos, aep_calc.get_TopFarm_cost_component(), 160, init_pos, boundary_type='square', record_id=None)
        tf.evaluate()
    assert tf.cost == -18.90684500124578