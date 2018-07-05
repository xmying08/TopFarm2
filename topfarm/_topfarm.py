from topfarm.constraint_components.boundary_component import BoundaryComp,\
    PolygonBoundaryComp
from topfarm.constraint_components.spacing_component import SpacingComp
from topfarm.plotting import PlotComp
from topfarm.utils import pos_from_case, latest_id
from topfarm.utils import shuffle_positions as spos
import os
import time
import numpy as np
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore', FutureWarning)
    from openmdao.api import Problem, ScipyOptimizeDriver, IndepVarComp, \
        SqliteRecorder


class TopFarm(object):
    """Optimize wind farm layout in terms of
    - Position of turbines
    [- Type of turbines: Not implemented yet]
    [- Height of turbines: Not implemented yet]
    [- Number of turbines: Not implemented yet]
    """

    def __init__(self, turbines, cost_comp, min_spacing, boundary,
                 boundary_type='convex_hull', plot_comp=None,
                 driver=ScipyOptimizeDriver(), record=False,
                 case_recorder_dir=os.getcwd(), rerun_case_id=None):
        self.min_spacing = min_spacing
        if rerun_case_id is None:
            turbines = np.array(turbines)
        elif rerun_case_id is 'latest':
            rerun_case_id = latest_id(case_recorder_dir)
            turbines = pos_from_case(rerun_case_id)
            print('*Initial positions loaded from file: {}\n'.format(
                    rerun_case_id))
        else:
            turbines = pos_from_case(rerun_case_id)
        n_wt = turbines.shape[0]
        self.initial_positions = turbines.T[0:2]
        self.n_wt = n_wt
        if boundary_type == 'polygon':
            self.boundary_comp = PolygonBoundaryComp(boundary[0], n_wt)
        else:
            self.boundary_comp = BoundaryComp(boundary[0], n_wt, boundary_type)
        self.problem = prob = Problem()
        indeps = prob.model.add_subsystem('indeps', IndepVarComp(),
                                          promotes=['*'])
        min_x, min_y = self.boundary_comp.vertices.min(0)
        mean_x, mean_y = self.boundary_comp.vertices.mean(0)
        design_var_kwargs = {}
        do = driver.options
        if 'optimizer' in do and do['optimizer'] == 'SLSQP':
            min_x, min_y, mean_x, mean_y = 0, 0, 1, 1  # scaling disturbs SLSQP
            # Default +/- sys.float_info.max does not work for SLSQP
            design_var_kwargs = {'lower': np.nan, 'upper': np.nan}
        indeps.add_output('turbineX', turbines[:, 0], units='m', ref0=min_x,
                          ref=mean_x)
        indeps.add_output('turbineY', turbines[:, 1], units='m', ref0=min_y,
                          ref=mean_y)
        indeps.add_output('boundary', self.boundary_comp.vertices, units='m')
        prob.model.add_subsystem('cost_comp', cost_comp, promotes=['*'])
        prob.driver = driver

        if record:
            timestr = time.strftime("%Y%m%d_%H%M%S")
            filename = 'cases_{}.sql'.format(timestr)
            case_recorder_filename = os.path.join(case_recorder_dir, filename)
            recorder = SqliteRecorder(case_recorder_filename)
            prob.driver.add_recorder(recorder)
            prob.driver.recording_options['record_desvars'] = True
            prob.driver.recording_options['record_responses'] = True
            prob.driver.recording_options['record_objectives'] = True
            prob.driver.recording_options['record_constraints'] = True

        prob.model.add_design_var('turbineX', **design_var_kwargs)
        prob.model.add_design_var('turbineY', **design_var_kwargs)
        prob.model.add_objective('cost')

        prob.model.add_subsystem('spacing_comp', SpacingComp(nTurbines=n_wt),
                                 promotes=['*'])
        prob.model.add_subsystem('bound_comp', self.boundary_comp,
                                 promotes=['*'])
        if plot_comp == "default":
            plot_comp = PlotComp()
        if plot_comp:
            plot_comp.n_wt = n_wt
            plot_comp.n_vertices = self.boundary_comp.vertices.shape[0]
            prob.model.add_subsystem('plot_comp', plot_comp, promotes=['*'])

        self.plot_comp = plot_comp
        prob.model.add_constraint('wtSeparationSquared', lower=np.zeros(int(((n_wt - 1.) * n_wt / 2.))) + (min_spacing)**2)
        prob.model.add_constraint('boundaryDistances', lower=np.zeros(self.boundary_comp.nVertices * n_wt))

        prob.setup(check=True, mode='fwd')


    def check(self, all=False, tol=1e-3):
        """Check gradient computations"""
        comp_name_lst = [comp.pathname for comp in self.problem.model.system_iter()
                         if comp._has_compute_partials and
                         (comp.pathname not in ['spacing_comp', 'bound_comp', 'plot_comp'] or (all and comp.pathname != 'plot_comp'))]
        print("checking %s" % ", ".join(comp_name_lst))
        res = self.problem.check_partials(includes=comp_name_lst, compact_print=True)
        for comp in comp_name_lst:
            var_pair = list(res[comp].keys())
            worst = var_pair[np.argmax([res[comp][k]['rel error'].forward for k in var_pair])]
            err = res[comp][worst]['rel error'].forward
            if err > tol:
                raise Warning("Mismatch between finite difference derivative of '%s' wrt. '%s' and derivative computed in '%s' is: %f" %
                              (worst[0], worst[1], comp, err))

    def evaluate(self):
        t = time.time()
        self.problem.run_model()
        print("Evaluated in\t%.3fs" % (time.time() - t))
        return self.get_cost(), self.turbine_positions

    def evaluate_gradients(self):
        t = time.time()
        res = self.problem.compute_totals(['cost'], wrt=['turbineX',
                                          'turbineY'], return_format='dict')
        print("Gradients evaluated in\t%.3fs" % (time.time() - t))
        return res

    def optimize(self):
        t = time.time()
        self.problem.run_driver()
        print("Optimized in\t%.3fs" % (time.time() - t))
        return self.get_cost(), np.array([self.problem['turbineX'], self.problem['turbineY']]).T

    def get_cost(self):
        return self.problem['cost'][0]

    @property
    def boundary(self):
        b = self.boundary_comp.vertices
        return np.r_[b, b[:1]]

    @property
    def turbine_positions(self):
        return np.array([self.problem['turbineX'], self.problem['turbineY']]).T

    def clean(self):
        for file in os.listdir(self.plot_comp.temp):
            if file.startswith('plot_') and file.endswith('.png'):
                os.remove(os.path.join(self.plot_comp.temp, file))

    def shuffle_positions(self, shuffle_type='rel', n_iter=1000,
                          step_size=0.1, pad=1.1, offset=5, plot=False,
                          verbose=False):
        if shuffle_type is not None:
            turbines = spos(self.boundary, self.n_wt, self.min_spacing,
                            self.turbine_positions, shuffle_type, n_iter,
                            step_size, pad, offset, plot, verbose)
            self.problem['turbineX'] = turbines.T[0]
            self.problem['turbineY'] = turbines.T[1]

    def animate(self, anim_time=10, verbose=False):
        if self.plot_comp.animate:
            self.plot_comp.run_animate(anim_time, verbose)
        else:
            if verbose:
                print('Animation requested but was not enabled for this '
                      'optimization. Set plot_comp.animate = True to enable')


def try_me():
    if __name__ == '__main__':
        from topfarm.cost_models.dummy import DummyCostPlotComp, DummyCost

        n_wt = 20
        random_offset = 5
        optimal = [(3, -3), (7, -7), (4, -3), (3, -7), (-3, -3), (-7, -7),
                   (-4, -3), (-3, -7)][:n_wt]
#        optimal = [(3, -3, 5, 1), (7, -7, 5, 1), (4, -3, 5, 1), (3, -7, 5, 1),
#                   (-3, -3, 5, 1), (-7, -7, 5, 1),
#                   (-4, -3, 5, 1), (-3, -7, 5, 1)][:n_wt]
        rotorDiameter = 1.0
        minSpacing = 2.0

        plot_comp = DummyCostPlotComp(optimal)
#        plot_comp.animate = True

        boundary = [[(0, 0), (6, 0), (6, -10), (0, -10)],]
        tf = TopFarm(optimal, DummyCost(optimal), minSpacing * rotorDiameter,
                     boundary=boundary, plot_comp=plot_comp, record=True)
        # tf.check()
        tf.shuffle_positions(shuffle_type='abs', offset=random_offset)
        tf.optimize()
        tf.animate()
        tf.clean()


try_me()
