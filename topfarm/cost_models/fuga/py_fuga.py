
import os
import pytest
import numpy as np
from topfarm.cost_models.cost_model_wrappers import AEPCostModelComponent
try:
    from topfarm.cost_models.fuga.Colonel.py_colonel import PyColonel
    from topfarm.cost_models.fuga.Colonel.py_colonel.py_colonel_exe import colonel_path
    fuga_path = colonel_path
except ImportError:
    PyColonel = object


class PyFuga(PyColonel):
    interface_version = 3

    def get_TopFarm_cost_component(self):
        n_wt = self.get_no_turbines()
        return AEPCostModelComponent(['turbineX', 'turbineY'], n_wt,
                                     lambda turbineX, turbineY, **kwargs: self.get_aep(np.array([turbineX, turbineY]).T)[0],  # only aep
                                     lambda turbineX, turbineY, **kwargs: self.get_aep_gradients(np.array([turbineX, turbineY]).T)[:2])  # only dAEPdx and dAEPdy


def try_me():
    if __name__ == '__main__':
        from topfarm.cost_models import fuga
        if not os.path.isdir(os.path.dirname(fuga.__file__) + "/Colonel/py_colonel"):
            pytest.xfail("Colonel submodule not found\n")
        pyFuga = PyFuga()
        pyFuga.setup(farm_name='Horns Rev 1',
                     turbine_model_path=fuga_path + 'LUTs-T/', turbine_model_name='Vestas_V80_(2_MW_offshore)[h=70.00]',
                     tb_x=[423974, 424033], tb_y=[6151447, 6150889],
                     mast_position=(0, 0, 70), z0=0.03, zi=400, zeta0=0,
                     farms_dir=fuga_path + 'LUTs-T/Farms/', wind_atlas_path='MyFarm\DEN05JBgr_7.813E_55.489N_7.4_5.lib')

        print(pyFuga.get_no_turbines())
        print(pyFuga.get_aep(np.array([[0, 0], [0, 1000]])))
        print(pyFuga.get_aep(np.array([[0, 1000], [0, 0]])))
        print(pyFuga.get_aep_gradients(np.array([[0, 0], [0, 100]])))


try_me()
