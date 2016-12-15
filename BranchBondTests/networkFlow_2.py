import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv

class MinCostFlow:
    def __init__(self, nodesfile, arcsfile):
        """Read in the csv data."""
        # Read in the nodes file
        self.node_data = pandas.read_csv(nodesfile)
        self.node_data.set_index(['Node'], inplace=True)
        self.node_data.sort_index(inplace=True)
        # Read in the arcs file
        self.arc_data = pandas.read_csv(arcsfile)
        self.arc_data.set_index(['Start','End'], inplace=True)
        self.arc_data.sort_index(inplace=True)

        self.node_set = self.node_data.index.unique()
        self.arc_set = self.arc_data.index.unique()

        self.createModel()

    def createModel(self):
        """Create the pyomo model given the csv data."""
        self.model = pyoenv.ConcreteModel()

        # Create sets
        self.model.node_set = pyoenv.Set( initialize=self.node_set )
        self.model.arc_set = pyoenv.Set( initialize=self.arc_set , dimen=2)

        # Create variables
        self.model.flow     = pyoenv.Var(self.model.arc_set,  domain=pyoenv.NonNegativeReals)
        self.model.pressure = pyoenv.Var(self.model.node_set, domain=pyoenv.NonNegativeReals)
        self.model.exterior = pyoenv.Var(self.model.node_set, domain=pyoenv.NonNegativeReals)

        # Create objective
        def obj_rule(model):
            return sum(abs(model.pressure[i]+self.arc_data.ix[(i,j),'dropCoeff']*model.flow[(i,j)]**2-model.pressure[i]) for (i,j) in self.arc_set)
        self.model.OBJ = pyoenv.Objective(rule=obj_rule, sense=pyoenv.minimize)

        # Flow Ballance rule
        def flow_bal_rule(model, n):
            arcs = self.arc_data.reset_index()
            preds = arcs[ arcs.End == n ]['Start']
            succs = arcs[ arcs.Start == n ]['End']
            return sum(model.flow[(p,n)] for p in preds)+self.node_data.ix[n, 'source'] == sum(model.flow[(n,s)] for s in succs)+self.node_data.ix[n, 'sink']+model.exterior[n]
        self.model.FlowBal = pyoenv.Constraint(self.model.node_set, rule=flow_bal_rule)

        # Upper forced rule
        def upper_forced_rule(model, n1, n2):
            e = (n1,n2)
            if self.arc_data.ix[e, 'maxForced'] < 0:
                return pyoenv.Constraint.Skip
            return model.flow[e] <= self.arc_data.ix[e, 'maxForced']
        self.model.UpperForced = pyoenv.Constraint(self.model.arc_set, rule=upper_forced_rule)
        # Lower forced rule
        def lower_forced_rule(model, n1, n2):
            e = (n1,n2)
            if self.arc_data.ix[e, 'minForced'] < 0:
                return pyoenv.Constraint.Skip
            return model.flow[e] >= self.arc_data.ix[e, 'minForced']
        self.model.LowerForced = pyoenv.Constraint(self.model.arc_set, rule=lower_forced_rule)
        # Upper exterior rule
        def upper_exterior_rule(model, n):
            if self.node_data.ix[n, 'maxExterior'] < 0:
                return pyoenv.Constraint.Skip
            return model.exterior[n] <= self.node_data.ix[n, 'maxExterior']
        self.model.UpperExterior = pyoenv.Constraint(self.model.node_set, rule=upper_exterior_rule)
        # Lower forced rule
        def lower_exterior_rule(model, n):
            if self.node_data.ix[n, 'minExterior'] < 0:
                return pyoenv.Constraint.Skip
            return model.exterior[n] >= self.node_data.ix[n, 'minExterior']
        self.model.LowerExterior = pyoenv.Constraint(self.model.node_set, rule=lower_exterior_rule)
        def upper_pressure_rule(model, n):
            if self.node_data.ix[n, 'maxP'] < 0:
                return pyoenv.Constraint.Skip
            return model.pressure[n] <= self.node_data.ix[n, 'maxP']
        self.model.UpperPressure = pyoenv.Constraint(self.model.node_set, rule=upper_pressure_rule)
        # Lower forced rule
        def lower_pressure_rule(model, n):
            if self.node_data.ix[n, 'minP'] < 0:
                return pyoenv.Constraint.Skip
            return model.pressure[n] >= self.node_data.ix[n, 'minP']
        self.model.LowerPressure = pyoenv.Constraint(self.model.node_set, rule=lower_pressure_rule)

    def solve(self):
        """Solve the model."""
        solver = pyomo.opt.SolverFactory('ipopt')
        results = solver.solve(self.model, tee=True, keepfiles=False   )#, options_string="mip_tolerances_integrality=1e-9 mip_tolerances_mipgap=0")

        if (results.solver.status != pyomo.opt.SolverStatus.ok):
            logging.warning('Check solver not ok?')
        if (results.solver.termination_condition != pyomo.opt.TerminationCondition.optimal):
            logging.warning('Check solver optimality?')


if __name__ == '__main__':
       sp = MinCostFlow('nodes.csv', 'bonds.csv')
       sp.solve()
       print( '\n\n---------------------------')
       print( 'Cost: ', sp.model.OBJ())
       print("Print values for each variable explicitly")
       s = ' %-20s  %-5.2f'
       print('\n %-20s  %-5s' % ('Bond', 'Flow'))
       for i in sp.model.flow:
           print(s % (sp.model.flow[i], sp.model.flow[i].value))
        #    print( str(sp.model.flow[i]), "%.1f" % sp.model.flow[i].value)
       print('\n %-20s  %-5s' % ('Node', 'Exterior'))
       for i in sp.model.exterior:
           print(s %(sp.model.exterior[i],sp.model.exterior[i].value))
       print('\n %-20s  %-5s' % ('Node', 'Exterior'))
       for i in sp.model.exterior:
           print(s %(sp.model.pressure[i],sp.model.pressure[i].value))
