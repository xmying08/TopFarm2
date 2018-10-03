import numpy as np
from topfarm.cost_models.cost_model_wrappers import CostModelComponent,\
    AEPCostModelComponent
from topfarm.constraint_components.spacing import SpacingConstraint
from topfarm.constraint_components.boundary import XYBoundaryConstraint
from topfarm import TopFarmProblem
from topfarm.easy_drivers import EasyScipyOptimizeDriver

boundary = [(0, 0), (6, 0), (6, -10), (0, -10)]  # turbine boundaries
initial = np.array([[6, 0], [6, -8], [1, 1], [-1, -8]])  # initial turbine layouts
optimal_with_constraints = np.array([[2.5, -3], [6, -7], [4.5, -3], [3, -7]])  # optimal turbine layout
min_spacing = 2  # min distance between turbines
optimal = np.array([[3, -3], [7, -7], [4, -3], [3, -7]])  # desired turbine layouts


def get_tf(cost_comp):
    return TopFarmProblem(
        dict(zip('xy', initial.T)),
        cost_comp=cost_comp,
        constraints=[SpacingConstraint(min_spacing), XYBoundaryConstraint(boundary)],
        driver=EasyScipyOptimizeDriver(disp=False))


def cost(x, y):
    opt_x, opt_y = optimal.T
    return np.sum((x - opt_x)**2 + (y - opt_y)**2)


def aep_cost(x, y):
    opt_x, opt_y = optimal.T
    return -np.sum((x - opt_x)**2 + (y - opt_y)**2)


def gradients(x, y):
    return (2 * x - 2 * optimal[:, 0]), (2 * y - 2 * optimal[:, 1])


def aep_gradients(x, y):
    return -(2 * x - 2 * optimal[:, 0]), -(2 * y - 2 * optimal[:, 1])


def test_CostModelComponent():
    tf = get_tf(CostModelComponent(['x', 'y'], 4, cost, gradients),)
    tf.optimize()
    np.testing.assert_array_almost_equal(tf.turbine_positions[:, :2], optimal_with_constraints, 5)


def testCostModelComponent_no_gradients():
    tf = get_tf(CostModelComponent(['x', 'y'], 4, cost, None))
    tf.optimize()
    np.testing.assert_array_almost_equal(tf.turbine_positions[:, :2], optimal_with_constraints, 5)


def testAEPCostModelComponent():
    tf = get_tf(AEPCostModelComponent(['x', 'y'], 4, aep_cost, aep_gradients))
    tf.optimize()
    np.testing.assert_array_almost_equal(tf.turbine_positions[:, :2], optimal_with_constraints, 5)
