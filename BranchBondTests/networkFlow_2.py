import time
import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv
import numpy as np

class FlowBalance:

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

    def updateParameters(self,dropCoeff_v,fan_v,heatFlow_v,forced_v):

        self.bond_data['dropCoeff'] = dropCoeff_v
        self.bond_data['fan']       = fan_v
        self.bond_data['heatFlow']  = heatFlow_v
        self.bond_data['forced']    = forced_v

        return self.bond_data


    def getHeatFlowStructure(self):



        return self.bond_data.ix[bond,'heatFlow']

    def createModel(self):
        """Create the pyomo model given the csv data."""
        self.model = pyoenv.ConcreteModel()

        # Create sets

        self.model.node_set = pyoenv.Set( ordered=True, initialize=self.node_set )
        self.model.bond_set = pyoenv.Set( ordered=True, initialize=self.bond_set , dimen=2)

        # Create variables
        self.model.flow     = pyoenv.Var(self.model.bond_set,
                                         domain=pyoenv.NonNegativeReals,initialize =1)
        self.model.pressure = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.NonNegativeReals,initialize =1)
        self.model.exterior = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.Reals,initialize =1)
        self.model.temper   = pyoenv.Var(self.model.node_set,
                                          domain=pyoenv.NonNegativeReals,initialize =298)
#-------# Flow Ballance ruleforced
        def flow_bal_rule(model, n):
            bonds = self.bond_data.reset_index()
            preds = bonds[ bonds.End == n ]['Start']
            succs = bonds[ bonds.Start == n ]['End']
            return sum(model.flow[(p,n)] for p in preds) + model.exterior[n] == sum(model.flow[(n,s)] for s in succs)
        self.model.FlowBal = pyoenv.Constraint(self.model.node_set, rule=flow_bal_rule)
#-------# Forced rule
        def forced_rule(model, n1, n2):
            e = (n1,n2)
            if not self.bond_data.ix[e, 'fan']:
                return pyoenv.Constraint.Skip
            return model.flow[e] == self.bond_data.ix[e, 'forced']
        self.model.Forced = pyoenv.Constraint(self.model.bond_set, rule=forced_rule)

#-------# Upper exterior rule
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
#-------# Upper pressure rule
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
#-------# Upper Temperature rule
        def upper_temp_rule(model, n):
            if self.node_data.ix[n, 'maxT'] < 0:
                return pyoenv.Constraint.Skip
            return model.temper[n] <= self.node_data.ix[n, 'maxT']
        self.model.UpperTemp = pyoenv.Constraint(self.model.node_set, rule=upper_temp_rule)
        # Lower Temperature rule
        def lower_temp_rule(model, n):
            if self.node_data.ix[n, 'minT'] < 0:
                return pyoenv.Constraint.Skip
            return model.temper[n] >= self.node_data.ix[n, 'minT']
        self.model.LowerTemp = pyoenv.Constraint(self.model.node_set, rule=lower_temp_rule)
#-------# Create objective
        def obj_rule(model):
            cP = 1000
            pressureEq = [((self.model.pressure[i] - self.model.pressure[j]
                          - self.bond_data.ix[(i,j),'dropCoeff'] * self.model.flow[(i,j)]**2)
                          if not self.bond_data.ix[(i,j),'fan'] else 0)
                          for (i,j) in self.model.bond_set]
            heatEq = []
            for n in self.model.node_set:
                bonds = self.bond_data.reset_index()
                preds = bonds[ bonds.End == n ]['Start']
                succs = bonds[ bonds.Start == n ]['End']

                nexterm = 0
                if self.node_data.ix[n ,'inlet']:
                    nextTerm  = cP * model.exterior[n]*self.node_data.ix[n ,'tempExt']
                if self.node_data.ix[n ,'outlet']:
                    nextTerm  = cP * model.exterior[n]*model.temper[n]

                nextTerm += ( cP * sum(model.flow[(p,n)]*model.temper[p]   for p in preds)
                            +      sum(self.bond_data.ix[(p,n),'heatFlow'] for p in preds)
                            - cP * sum(model.flow[(n,s)]*model.temper[n]   for s in succs))
                # print([self.bond_data.ix[(p,n),'heatFlow'] for p in preds])

                heatEq.append(nextTerm)

            totalEq = pressureEq + heatEq

            return(sum(np.square(totalEq)))
        self.model.OBJ = pyoenv.Objective(rule=obj_rule, sense=pyoenv.minimize)


    def solve(self):

        """Solve the model."""
        solver = pyomo.opt.SolverFactory('ipopt')
        instance = self.model.create_instance()
        results = solver.solve(instance, tee=True, keepfiles=False )#, options_string="mip_tolerances_integrality=1e-9 mip_tolerances_mipgap=0")

        if (results.solver.status != pyomo.opt.SolverStatus.ok):
            logging.warning('Check solver not ok?')
        if (results.solver.termination_condition != pyomo.opt.TerminationCondition.optimal):
            logging.warning('Check solver optimality?')
        # flowList     = [self.model.flow[i].value     for i in self.model.flow]
        # externalList = [self.model.exterior[i].value for i in self.model.exterior]
        # pressureList = [self.model.pressure[i].value for i in self.model.pressure]

    def printInfo(self):
        print( '\n\n---------------------------')
        print( 'Convergence: ', self.model.OBJ())
        print("Print values for each variable explicitly")
        s = ' %-50s  %-5.2f'

        print('\n %-50s  %-5s' % ('Bond', 'Flow'))
        for i in self.model.flow:
            print(s % (i, self.model.flow[i].value))

        print('\n %-50s  %-5s' % ('Node', 'Exterior'))
        for i in self.model.exterior:
            print(s % (i,self.model.exterior[i].value))

        print('\n %-50s  %-5s' % ('Node', 'Pressure'))
        for i in self.model.exterior:
            print(s %(i,self.model.pressure[i].value))

        print('\n %-50s  %-5s' % ('Node', 'Temperature'))
        for i in self.model.temper:
            print(s %(i,self.model.temper[i].value))

if __name__ == '__main__':
       calc_begining_time          = time.time()
       sp = FlowBalance('nodes.csv', 'bonds.csv')
       sp.solve()
       print('Calculation took     :   %f seconds'  % ( time.time() - calc_begining_time))
       
