import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv
import numpy as np

class MinCostFlow:
    def __init__(self, nodesfile, bondsfile):
        """Read in the csv data."""
        # Read in the nodes file
        self.node_data = pandas.read_csv(nodesfile)
        self.node_data.set_index(['Node'], inplace=True)
        self.node_data.sort_index(inplace=True)
        # Read in the bonds file
        self.bond_data = pandas.read_csv(bondsfile)
        self.bond_data.set_index(['Start','End'], inplace=True)
        self.bond_data.sort_index(inplace=True)

        self.node_set = self.node_data.index.unique()
        self.bond_set = self.bond_data.index.unique()

        self.createModel()
    def createModel(self):
        """Create the pyomo model given the csv data."""
        self.model = pyoenv.ConcreteModel()

        # Create sets

        self.model.node_set = pyoenv.Set( ordered=True, initialize=self.node_set )
        self.model.bond_set = pyoenv.Set( ordered=True, initialize=self.bond_set , dimen=2)

        # Create variables
        self.model.flow     = pyoenv.Var(self.model.bond_set,
                                         domain=pyoenv.NonNegativeReals,initialize =1)
                                        #  initialize = {('entrance','room'):14,
                                        #                ('room','exit1'):7,
                                        #                ('room','exit2'):7,
                                        #                ('exit1','entrance'):2,
                                        #                ('exit2','entrance'):2})

        self.model.pressure = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.NonNegativeReals,initialize =1)
                                        #  initialize={'entrance':1245,
                                        #              'room':1049,
                                        #              'exit1':1000,
                                        #              'exit2':1000})

        self.model.exterior = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.Reals,initialize =1)
                                        #  initialize={'entrance':10,
                                        #              'room':0,
                                        #              'exit1':-5,
                                        #              'exit2':-5})

        # Create objective
        def obj_rule(model):
                # pressureVector     = np.array([self.model.pressure[i].value for i in self.model.node_set])
            dummy = [((self.model.pressure[i]- self.model.pressure[j] - self.bond_data.ix[(i,j),'dropCoeff']*self.model.flow[(i,j)]**2) if not self.bond_data.ix[(i,j),'Fan'] else 0) for (i,j) in self.model.bond_set]
            # print ([((self.model.pressure[i].value- self.model.pressure[j].value) if not self.bond_data.ix[(i,j),'Fan'] else 0) for (i,j) in self.model.bond_set])
            # print ([((self.bond_data.ix[(i,j),'dropCoeff']*self.model.flow[(i,j)].value**2) if not self.bond_data.ix[(i,j),'Fan'] else 0) for (i,j) in self.model.bond_set])
            # print ([((self.model.pressure[i].value- self.model.pressure[j].value - self.bond_data.ix[(i,j),'dropCoeff']*self.model.flow[(i,j)].value**2) if not self.bond_data.ix[(i,j),'Fan'] else 0) for (i,j) in self.model.bond_set])
            return(sum(np.square(dummy)))
        self.model.OBJ = pyoenv.Objective(rule=obj_rule, sense=pyoenv.minimize)

        # Flow Ballance rule
        def flow_bal_rule(model, n):
            bonds = self.bond_data.reset_index()
            preds = bonds[ bonds.End == n ]['Start']
            succs = bonds[ bonds.Start == n ]['End']
            return sum(model.flow[(p,n)] for p in preds) + model.exterior[n] == sum(model.flow[(n,s)] for s in succs)
        self.model.FlowBal = pyoenv.Constraint(self.model.node_set, rule=flow_bal_rule)
        # Upper forced rule
        def upper_forced_rule(model, n1, n2):
            e = (n1,n2)
            if self.bond_data.ix[e, 'maxForced'] < 0:
                return pyoenv.Constraint.Skip
            return model.flow[e] <= self.bond_data.ix[e, 'maxForced']
        self.model.UpperForced = pyoenv.Constraint(self.model.bond_set, rule=upper_forced_rule)
        # Lower forced rule
        def lower_forced_rule(model, n1, n2):
            e = (n1,n2)
            if self.bond_data.ix[e, 'minForced'] < 0:
                return pyoenv.Constraint.Skip
            return model.flow[e] >= self.bond_data.ix[e, 'minForced']
        self.model.LowerForced = pyoenv.Constraint(self.model.bond_set, rule=lower_forced_rule)
        # Upper exterior rule
        def upper_exterior_rule(model, n):
            # if self.node_data.ix[n, 'maxExterior'] < 0:
            #     return pyoenv.Constraint.Skip
            return model.exterior[n] <= self.node_data.ix[n, 'maxExterior']
        self.model.UpperExterior = pyoenv.Constraint(self.model.node_set, rule=upper_exterior_rule)
        # Lower exterior rule
        def lower_exterior_rule(model, n):
            # if self.node_data.ix[n, 'minExterior'] < 0:
            #     return pyoenv.Constraint.Skip
            return model.exterior[n] >= self.node_data.ix[n, 'minExterior']
        self.model.LowerExterior = pyoenv.Constraint(self.model.node_set, rule=lower_exterior_rule)
        # Upper pressure rule
        def upper_pressure_rule(model, n):
            if self.node_data.ix[n, 'maxP'] < 0:
                return pyoenv.Constraint.Skip
            return model.pressure[n] <= self.node_data.ix[n, 'maxP']
        self.model.UpperPressure = pyoenv.Constraint(self.model.node_set, rule=upper_pressure_rule)
        # Lower pressure rule
        def lower_pressure_rule(model, n):
            if self.node_data.ix[n, 'minP'] < 0:
                return pyoenv.Constraint.Skip
            return model.pressure[n] >= self.node_data.ix[n, 'minP']
        self.model.LowerPressure = pyoenv.Constraint(self.model.node_set, rule=lower_pressure_rule)
    def solve(self):
        """Solve the model."""
        solver = pyomo.opt.SolverFactory('ipopt')
        results = solver.solve(self.model, tee=True, keepfiles=False )#, options_string="mip_tolerances_integrality=1e-9 mip_tolerances_mipgap=0")

        if (results.solver.status != pyomo.opt.SolverStatus.ok):
            logging.warning('Check solver not ok?')
        if (results.solver.termination_condition != pyomo.opt.TerminationCondition.optimal):
            logging.warning('Check solver optimality?')
        flowList     = [self.model.flow[i].value for i in self.model.flow]
        externalList = [self.model.exterior[i].value for i in self.model.exterior]
        pressureList = [self.model.pressure[i].value for i in self.model.pressure]
        print(flowList)

    def printInfo(self):
        print( '\n\n---------------------------')
        print( 'Convergence: ', self.model.OBJ())
        print("Print values for each variable explicitly")
        s = ' %-20s  %-5.2f'

        print('\n %-50s  %-5s' % ('Bond', 'Flow'))
        for i in self.model.flow:
            print(s % (i, self.model.flow[i].value))

        print('\n %-20s  %-5s' % ('Node', 'Exterior'))
        for i in self.model.exterior:
            print(s % (i,self.model.exterior[i].value))

        print('\n %-20s  %-5s' % ('Node', 'Exterior'))
        for i in self.model.exterior:
            print(s %(i,self.model.pressure[i].value))
if __name__ == '__main__':
       sp = MinCostFlow('nodes.csv', 'bonds.csv')
       sp.solve()
    #    sp.printInfo()
