import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv
import numpy as np

import config

class air_volume_GBM:


    def __init__(self):
        self.dt = config.dt
        self.createModel()
        # self.air_int            = 400     #[kJ/K] Thermal inertia for the oil bath
        # self.airC               = 10      #[kW/K] Heat carryng capacity of the water current
        self.airCold_Limit      = 38
        self.exchCoeffs         = [0.001, 1, 1.5, 2, 2.556]
        self.cover_trans        = [0.001, 0.25, 0.5, 1, 1.5]  #[kW/K]

        self.coverOut      = 0
        self.componentsIn  = 0
        self.exchOut       = 0
        self.alarm         = False
        self.exchMode      = 0
        self.exchLag       = 0

        self.towerMode     = 0
        self.towerLag      = 0

    def createModel(self):
        self.model = pyoenv.AbstractModel()
        # Create sets
        self.model.node_set = pyoenv.Set(ordered = True,dimen=1)
        self.model.bond_set = pyoenv.Set(ordered = True,dimen=2)
        # Create parameters
        self.model.maxExterior = pyoenv.Param(self.model.node_set, mutable= True)
        self.model.minExterior = pyoenv.Param(self.model.node_set, mutable= True)
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
#-------# Forced rule
        def forced_rule(model, n1, n2):
            if not model.fan[(n1,n2)]:
                return pyoenv.Constraint.Skip
            else:
                return model.flow[(n1,n2)] == model.forced[(n1,n2)]
#-------# Exterior rule
        def exterior_rule(model, node):
            if not (model.inlet[node] or model.outlet[node]):
                 return model.exterior[node] == 0
            else:
                 return (model.minExterior[node],model.exterior[node],model.maxExterior[node])
#-------# Pressure rule
        def pressure_rule(model, node):
            return (model.minP[node],model.pressure[node],model.maxP[node])
#-------# Temperature rule
        def temp_rule(model, node):
            return (model.minT[node],model.temper[node],model.maxT[node])
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

        self.model.OBJ      = pyoenv.Objective(rule=obj_rule, sense=pyoenv.minimize)
        self.model.FlowBal  = pyoenv.Constraint(self.model.node_set, rule=flow_bal_rule)
        self.model.Forced   = pyoenv.Constraint(self.model.bond_set, rule=forced_rule)
        self.model.Exterior = pyoenv.Constraint(self.model.node_set, rule=exterior_rule)
        self.model.Pressure = pyoenv.Constraint(self.model.node_set, rule=pressure_rule)
        self.model.Temp     = pyoenv.Constraint(self.model.node_set, rule=temp_rule)

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

    def updateAirFlows(self,machineState):
        self.instance.minExterior['Air_treatment_system']                 = self.airTreatmentInFlow(machineState)
        self.instance.maxExterior['Air_treatment_system']                 = self.instance.minExterior['Air_treatment_system']
        self.instance.forced[('Tower_top', 'Converter_inlet')]            = self.converterPlatformFlow(machineState)
        self.instance.forced[('Tower_top', 'Switchgear_inlet')]           = self.switchgearPlatformFlow(machineState)
        self.instance.forced[('Tower_top', 'Transformer_inlet')]          = self.transformerPlatformFlow(machineState)
        self.instance.forced[('Nacelle_top_rear', 'Nacelle_bottom_rear')] = self.nacelleCoolingFlow(machineState)


    def updateHeatFlows(self,machineState):
        self.instance.heatFlow[('Air_treatment_system', 'Tower_top')]           = self.airTreatmentHeat(machineState)
        self.instance.heatFlow[('Converter_inlet', 'Converter_platform')]       = self.converterPlatformHeat(machineState)
        self.instance.heatFlow[('Converter_platform', 'Tower_middle')]          = self.towerUpHeat_3(machineState)
        self.instance.heatFlow[('Switchgear_inlet', 'Switchgear_platform')]     = self.switchgearPlatformHeat(machineState)
        self.instance.heatFlow[('Switchgear_platform', 'Transformer_platform')] = self.towerUpHeat_1(machineState)
        self.instance.heatFlow[('Tower_middle', 'Tower_top')]                   = self.towerUpHeat_4(machineState)
        self.instance.heatFlow[('Tower_top', 'Converter_inlet')]                = 0
        self.instance.heatFlow[('Tower_top', 'Switchgear_inlet')]               = 0
        self.instance.heatFlow[('Tower_top', 'Tower_leakage_exterior')]         = 0
        self.instance.heatFlow[('Tower_top', 'Transformer_inlet')]              = 0
        self.instance.heatFlow[('Transformer_inlet', 'Transformer_platform')]   = self.transformerPlatformHeat(machineState)
        self.instance.heatFlow[('Transformer_platform', 'Converter_platform')]  = self.towerUpHeat_2(machineState)
        self.instance.heatFlow[('Tower_top', 'Nacelle_bottom_front')]           = 0
        self.instance.heatFlow[('Nacelle_bottom_rear', 'Nacelle_bottom_front')] = self.driveTrainHeatLower(machineState)
        self.instance.heatFlow[('Nacelle_bottom_front', 'Nacelle_top_front')]   = self.driveTrainHeatFront(machineState)
        self.instance.heatFlow[('Nacelle_top_front', 'Nacelle_top_rear')]       = self.driveTrainHeatUpper(machineState)
        self.instance.heatFlow[('Nacelle_top_rear', 'Nacelle_bottom_rear')]     = self.nacelleCooling(machineState)
        self.instance.heatFlow[('Nacelle_bottom_rear', 'Nacelle_top_rear')]     = self.driveTrainHeatRear(machineState)
        self.instance.heatFlow[('Nacelle_top_front', 'Hub')]                    = 0
        self.instance.heatFlow[('Nacelle_bottom_front', 'Hub')]                 = 0
        self.instance.heatFlow[('Hub', 'Hub_leakage_exterior')]                 = 0

    def airTreatmentHeat(self,machineState):
        return 1000
    def converterPlatformHeat(self,machineState):
        return machineState.converter.lossesAir*1000
    def transformerPlatformHeat(self,machineState):
        return machineState.transformer.lossesAir*1000
    def switchgearPlatformHeat(self,machineState):
        return 2000
    def driveTrainHeatLower(self,machineState):
        return 1000*(machineState.gearbox.lossesAir + machineState.generator.lossesAir)/5 +5000
    def driveTrainHeatFront(self,machineState):
        return 1000*(machineState.gearbox.lossesAir + machineState.generator.lossesAir)/5
    def driveTrainHeatUpper(self,machineState):
        return 1000*2*(machineState.gearbox.lossesAir + machineState.generator.lossesAir)/5
    def driveTrainHeatRear(self,machineState):
        return 1000*(machineState.gearbox.lossesAir + machineState.generator.lossesAir)/5
    def nacelleCooling(self,machineState):
        limitsUp=  [ 0, 30, 33, 36, 40]
        limitsDown=[ 0, 28, 31, 34, 37]
        airTemp = machineState.air_component.temperature['Nacelle_bottom_rear']
        if airTemp > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if airTemp > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (airTemp < limitsDown[self.exchMode]) & (self.exchLag<1) :
            for i in range(self.exchMode,0,-1):
                if self.airMiddle < limitsDown[i]:
                    self.exchMode = i-1
        airCold = machineState.air_component.temperature['Nacelle_bottom_rear']
        if airCold > self.airCold_Limit:
            self.alarm = True
        else:
            self.alarm = False
        return -1000*(machineState.air_component.temperature['Nacelle_top_rear'] -machineState.Tamb)*self.exchCoeffs[self.exchMode]
    def towerUpHeat_1(self,machineState):
        return -1000*(machineState.air_component.temperature['Switchgear_platform']-machineState.Tamb)*2.5
    def towerUpHeat_2(self,machineState):
        return -1000*(machineState.air_component.temperature['Transformer_platform']-machineState.Tamb)*2.5
    def towerUpHeat_3(self,machineState):
        return -1000*(machineState.air_component.temperature['Converter_platform']-machineState.Tamb)*2.5
    def towerUpHeat_4(self,machineState):
        return -1000*(machineState.air_component.temperature['Tower_middle']-machineState.Tamb)*2.5
    def airTreatmentInFlow(self,machineState):
        return 0.807
    def converterPlatformFlow(self,machineState):
        return 1.72
    def transformerPlatformFlow(self,machineState):
        return 1.72
    def switchgearPlatformFlow(self,machineState):
        return 1.39
    def nacelleCoolingFlow(self,machineState):
        flowsSet = [ 0.5, 2.45, 4.9, 7.36, 9.81]
        return flowsSet[self.exchMode]

    def advanceTemperatures(self):
        for node in self.instance.node_set:
               self.instance.tempPre[node]= self.instance.temper[node].value
    def resultsToDictionary(self):
        temperatureDict={}
        for node in self.instance.node_set:
            temperatureDict.update({node:self.instance.temper[node].value})
        flowDict={}
        heatDict={}
        for bond in self.instance.bond_set:
            flowDict.update({bond:self.instance.flow[bond].value})
            heatDict.update({bond:self.instance.heatFlow[bond].value})
        heatDict.update({'exchMode':self.exchMode})
        return [temperatureDict,flowDict,heatDict]
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
