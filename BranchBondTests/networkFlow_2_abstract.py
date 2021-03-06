#!/usr/bin/env python

import time
import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv
import numpy as np

class FlowBalance:

    def __init__(self):
        self.dt = 10
        self.createModel()

    def createModel(self):
        self.model = pyoenv.AbstractModel()
        # Create sets
        self.model.node_set = pyoenv.Set(ordered = True,dimen=1)
        self.model.bond_set = pyoenv.Set(ordered = True,dimen=2)
        # Create parameters
        self.model.maxExterior = pyoenv.Param(self.model.node_set)
        self.model.minExterior = pyoenv.Param(self.model.node_set)
        self.model.maxP        = pyoenv.Param(self.model.node_set)
        self.model.minP        = pyoenv.Param(self.model.node_set)
        self.model.maxT        = pyoenv.Param(self.model.node_set)
        self.model.minT        = pyoenv.Param(self.model.node_set)
        self.model.tempExt     = pyoenv.Param(self.model.node_set, mutable= True)
        self.model.inlet       = pyoenv.Param(self.model.node_set)
        self.model.outlet      = pyoenv.Param(self.model.node_set)
        self.model.airMass     = pyoenv.Param(self.model.node_set)
        self.model.tempPre     = pyoenv.Param(self.model.node_set, mutable= True)

        self.model.fan         = pyoenv.Param(self.model.bond_set)
        self.model.forced      = pyoenv.Param(self.model.bond_set, mutable= True)
        self.model.dropCoeff   = pyoenv.Param(self.model.bond_set)
        self.model.heatFlow    = pyoenv.Param(self.model.bond_set, mutable= True)
        # Create variables
        self.model.flow     = pyoenv.Var(self.model.bond_set, domain=pyoenv.NonNegativeReals, initialize =0)
        self.model.pressure = pyoenv.Var(self.model.node_set, domain=pyoenv.NonNegativeReals, initialize =0)
        self.model.exterior = pyoenv.Var(self.model.node_set, domain=pyoenv.Reals,            initialize = 0)
        self.model.temper   = pyoenv.Var(self.model.node_set, domain=pyoenv.NonNegativeReals, initialize = 24)
#-------# Flow Ballance ruleforced
        def flow_bal_rule(model, node):
            bonds = model.bond_set
            preds = [i for (i,j) in bonds if j == node]#bonds[ bonds[:][1] == node ][0]
            succs = [j for (i,j) in bonds if i == node]#bonds[ bonds[:][0] == node ][1]
            return sum(model.flow[(p,node)] for p in preds) + model.exterior[node] == sum(model.flow[(node,s)] for s in succs)
        self.model.FlowBal = pyoenv.Constraint(self.model.node_set, rule=flow_bal_rule)
#-------# Forced rule
        def forced_rule(model, n1, n2):
            if not model.fan[(n1,n2)]:
                return pyoenv.Constraint.Skip
            else:
                return model.flow[(n1,n2)] == model.forced[(n1,n2)]
        self.model.Forced = pyoenv.Constraint(self.model.bond_set, rule=forced_rule)
#-------# Exterior rule
        def exterior_rule(model, node):
            if not (model.inlet[node] or model.outlet[node]):
                 return model.exterior[node] == 0
            else:
                 return (model.minExterior[node],model.exterior[node],model.maxExterior[node])
        self.model.LowerExterior = pyoenv.Constraint(self.model.node_set, rule=exterior_rule)
#-------# Pressure rule
        def pressure_rule(model, node):
            return (model.minP[node],model.pressure[node],model.maxP[node])
        self.model.UpperPressure = pyoenv.Constraint(self.model.node_set, rule=pressure_rule)
#-------# Temperature rule
        def temp_rule(model, node):
            return (model.minT[node],model.temper[node],model.maxT[node])
        self.model.UpperTemp = pyoenv.Constraint(self.model.node_set, rule=temp_rule)
#-------# Create objective
        def obj_rule(model):
            cP = 1000
            pressureEq = [((model.pressure[i] - model.pressure[j]
                          - model.dropCoeff[(i,j)] * model.flow[(i,j)]*abs(model.flow[(i,j)]))
                          if not model.fan[(i,j)] else 0)
                          for (i,j) in model.bond_set]
            heatEq = []
            for node in model.node_set:
                bonds = model.bond_set
                preds = [i for (i,j) in bonds if j == node]
                succs = [j for (i,j) in bonds if i == node]

                nexterm = 0
                if model.inlet[node]:
                    nextTerm  = cP * model.exterior[node]*model.tempExt[node]
                if model.outlet[node]:
                    nextTerm  = cP * model.exterior[node]*model.tempPre[node]

                nextTerm += (  cP*sum(model.flow[(p,node)]*model.temper[p]     for p in preds)
                             - cP*sum(model.flow[(node,s)]*model.temper[node]  for s in succs)
                             +    sum(model.heatFlow[(p,node)]                 for p in preds)
                             + cP*model.airMass[node]*(model.tempPre[node]-model.temper[node])/self.dt)
                heatEq.append(nextTerm)

            totalEq = pressureEq + heatEq

            return(sum(np.square(totalEq)))
        self.model.OBJ = pyoenv.Objective(rule=obj_rule, sense=pyoenv.minimize)


    def solve(self):

        """Solve the model."""
        solver = pyomo.opt.SolverFactory('ipopt')
        self.results = solver.solve(self.instance, tee=False, keepfiles=False )#, options_string="mip_tolerances_integrality=1e-9 mip_tolerances_mipgap=0")

        if (self.results.solver.status != pyomo.opt.SolverStatus.ok):
            logging.warning('Check solver not ok?')
        if (self.results.solver.termination_condition != pyomo.opt.TerminationCondition.optimal):
            logging.warning('Check solver optimality?')

    def loadModelData(self, nodesfile, bondsfile):
        data = pyoenv.DataPortal()
        data.load(filename=nodesfile,param=(self.model.minExterior,
                                            self.model.maxExterior,
                                            self.model.minP,
                                            self.model.maxP,
                                            self.model.minT,
                                            self.model.maxT,
                                            self.model.tempExt,
                                            self.model.inlet,
                                            self.model.outlet,
                                            self.model.airMass,
                                            self.model.tempPre),
                                            index=self.model.node_set)
        data.load(filename=bondsfile,param=(self.model.dropCoeff,
                                            self.model.fan,
                                            self.model.heatFlow,
                                            self.model.forced),
                                            index=self.model.bond_set)

        self.instance = self.model.create_instance(data)

    def updatHeatFlows(self):
        self.instance.heatFlow[('Air_treatment_system', 'Tower_top')]           = self.airTreatmentHeat()
        self.instance.heatFlow[('Converter_inlet', 'Converter_platform')]       = self.converterPlatformHeat()
        self.instance.heatFlow[('Converter_platform', 'Tower_middle')]          = self.towerUpHeat_3()
        self.instance.heatFlow[('Switchgear_inlet', 'Switchgear_platform')]     = self.switchgearPlatformHeat()
        self.instance.heatFlow[('Switchgear_platform', 'Transformer_platform')] = self.towerUpHeat_1()
        self.instance.heatFlow[('Tower_middle', 'Tower_top')]                   = self.towerUpHeat_4()
        self.instance.heatFlow[('Tower_top', 'Converter_inlet')]                = 0
        self.instance.heatFlow[('Tower_top', 'Switchgear_inlet')]               = 0
        self.instance.heatFlow[('Tower_top', 'Tower_leakage_exterior')]         = 0
        self.instance.heatFlow[('Tower_top', 'Transformer_inlet')]              = 0
        self.instance.heatFlow[('Transformer_inlet', 'Transformer_platform')]   = self.transformerPlatformHeat()
        self.instance.heatFlow[('Transformer_platform', 'Converter_platform')]  = self.towerUpHeat_2()
        self.instance.heatFlow[('Tower_top', 'Nacelle_bottom_front')]           = 0
        self.instance.heatFlow[('Nacelle_bottom_rear', 'Nacelle_bottom_front')] = self.driveTrainHeatLower()
        self.instance.heatFlow[('Nacelle_bottom_front', 'Nacelle_top_front')]   = self.driveTrainHeatFront()
        self.instance.heatFlow[('Nacelle_top_front', 'Nacelle_top_rear')]       = self.driveTrainHeatUpper()
        self.instance.heatFlow[('Nacelle_top_rear', 'Nacelle_bottom_rear')]     = self.nacelleCooling()
        self.instance.heatFlow[('Nacelle_bottom_rear', 'Nacelle_top_rear')]     = self.driveTrainHeatRear()
        self.instance.heatFlow[('Nacelle_top_front', 'Hub')]                    = 0
        self.instance.heatFlow[('Nacelle_bottom_front', 'Hub')]                 = 0
        self.instance.heatFlow[('Hub', 'Hub_leakage_exterior')]                 = 0
    def airTreatmentHeat(self):
        return 1000
    def converterPlatformHeat(self):
        return 1000
    def switchgearPlatformHeat(self):
        return 1000
    def transformerPlatformHeat(self):
        return 1000
    def driveTrainHeatLower(self):
        return 1000
    def driveTrainHeatFront(self):
        return 1000
    def driveTrainHeatUpper(self):
        return 1000
    def driveTrainHeatRear(self):
        return 1000
    def nacelleCooling(self):
        return -1000
    def towerUpHeat_1(self):
        return -1000
    def towerUpHeat_2(self):
        return -1000
    def towerUpHeat_3(self):
        return -1000
    def towerUpHeat_4(self):
        return -1000

    def advanceTemperatures(self):
        for node in self.instance.node_set:
               self.instance.tempPre[node]= self.instance.temper[node].value

    def printInfo(self):
        print( '\n\n---------------------------')
        print( 'Convergence: ', self.instance.OBJ())
        print("Print values for each variable explicitly")
        s = ' %-50s  %-13.2f  %-13.2f  %-13.2f  %-13.2f'

        print('\n %-50s  %-13s %-13s' % ('Bond', 'Flow', 'Heat'))
        for i in self.instance.flow:
            print(' %-50s  %-13.2f  %-13.2f' % (i, self.instance.flow[i].value, self.instance.heatFlow[i].value))
        print('\n %-50s  %-13s  %-13s  %-13s  %-13s' % ('Node', 'Temperature', 'Temp[-1]', 'Pressure', 'Exterior'))
        for node in self.instance.node_set:
            print(s %(node, self.instance.temper[node].value, self.instance.tempPre[node].value, self.instance.pressure[node].value, self.instance.exterior[node].value))

if __name__ == '__main__':
       calc_begining_time= time.time()
       sp = FlowBalance()
       sp.loadModelData('nodes.tab', 'bonds.tab')

       for i in range(900):
           sp.solve()
           sp.printInfo()
           print('Step: ',i,'  Calculation took     :   %f seconds'  % ( time.time() - calc_begining_time))
           sp.advanceTemperatures()
           sp.updatHeatFlows()
