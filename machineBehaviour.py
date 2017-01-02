import copy
import time
import math
import numpy as np
import datetime
import pyomo
import pandas
import pyomo.opt
import pyomo.environ as pyoenv

from thermal_inertia_tools import *
import config

def counted(fn):
    def wrapper(*args, **kwargs):
        wrapper.called+= 1
        return fn(*args, **kwargs)
    wrapper.called= 0
    wrapper.__name__= fn.__name__
    return wrapper

# Object that represents the wind turbine generator an a certain time
class machineState(object):
    # self.air_volume_GBM = air_volume_GBM('nodes.csv', 'bonds.csv')
    # self.machineTimeStep       = counter(machineTimeStep)
    def __init__(self,T_0):
        self.transformer = tr_component(T_0)
        self.converter   = cv_component(T_0)
        self.generator   = gn_component(T_0)
        self.gearbox     = gb_component(T_0)
        self.nacelle     = nac_component(T_0)
        self.power       = 0
        self.potential   = 0
        self.PF          = 1
        self.V           = 1
        self.time        = datetime.datetime(2013, 7, 5, 0, 0)
        self.wind        = 0
        self.Tamb        = T_0
        self.start_time  = time.time()
        # self.machineTimeStep       = counter(machineState.machineTimeStep)

    # Returns a new instance of the machine state evolved for the ambient conditions given
    @counted
    def machineTimeStep(self, wind, PF, V, Tamb):
        newTime = copy.deepcopy(self)                                               # Copy old instance
        newTime.time += datetime.timedelta(seconds = config.dt )                    # Advance time
        newTime.wind = wind                                                         # Load new wind
        newTime.potential = newTime.powerFunction()                                 # Calculate potential power production
        newTime.derateIfNeeded(newTime.potential,PF,V,Tamb)                         # Modify production if derating required
        newTime.transformer.timeStep(newTime.power,newTime.PF,newTime.V,Tamb)       # Calculate TRANSFORMER
        newTime.converter.timeStep(newTime.transformer.powerIN,newTime.PF,newTime.V,Tamb) # Calculate CONVERTER
        newTime.generator.timeStep(newTime.converter.powerIN,Tamb)                  # Calculate GENERATOR
        newTime.gearbox.timeStep(newTime.generator.powerIN,Tamb)                    # Calculate GEARBOX
        newTime.nacelle.timeStep(newTime.generator.losses*(1-newTime.generator.split),newTime.gearbox.losses*(1-newTime.gearbox.split),Tamb)
        # newTime.air_volume_GBM.solve()
        # newTime.ain_volume.dump_GBM_to_store()

        return newTime
    # Returns interpolation of power produtcion given a  wind speed
    def powerFunction(self):
        return  np.interp(self.wind, config.powerCurve[0], config.powerCurve[1])
    # Returns a vector with the alarm state for all components
    def getAlarms(self):
        return [self.transformer.alarm, self.converter.alarm, self.generator.alarm, self.gearbox.alarm, self.nacelle.alarm]
    # Evaluates the need to derate and aplies the necessary production modifications at the beginning of the timestep
    def derateIfNeeded(self, power, PF, V, Tamb):
        alarms = self.getAlarms()
        if any(alarms):
            maxOut  = [self.transformer.maxOut(Tamb), self.converter.maxOut(Tamb), self.generator.maxOut(Tamb), self.gearbox.maxOut(Tamb)]
            achievable = min(maxOut)
            if achievable > power:
                combFactor = power/achievable
                self.power = power
                if combFactor < PF:
                    self.V  = max(0.9,combFactor/PF)
                    self.PF = PF
                else:
                    self.V  = 1
                    self.PF = combFactor
            else:
                self.power = achievable
                self.PF    = 1
                self.V     = 1
        else:
            self.power       = power
            self.PF          = PF
            self.V           = V
            self.Tamb        = Tamb
    # Deactivate the temperature alarms for testing
    def removeTempLimits(self):
        self.transformer.oilHot_tempLimit  = 10000
        self.converter.waterCold_tempLimit = 10000
        self.generator.waterCold_tempLimit = 10000
        self.gearbox.oilCold_tempLimit     = 10000
        self.nacelle.airCold_Limit         = 10000
# Object which holds the behaviour parameters and the variables that define the state of a TRANSFORMER
class tr_component(object):
    solid_oil_trans    = 5.333   #[kW/K] Winddings ---> Oil bath
    oil_water_trans    = 2.491   #[kW/K] Oil Water Heat Exchager
    solid_int          = 4370    #[kJ/K] Thermal inertia for the solid parts
    oil_int            = 8650    #[kJ/K] Thermal inertia for the oil bath
    water_int          = 616     #[kJ/K] Thermal inertia for the water in the circuit
    oilC               = 9.12    #[kW/K] Heat carryng capacity of the oil current
    waterC             = 19.5    #[kW/K] Heat carryng capacity of the water current
    split              = 0.95    #       Estimate of the losses extracted by the liquid circuit
    oilHot_tempLimit   = 120     #[C]    Alarm imposed for the oil temperature
    exchCoeffs         = [0.25, 1.18, 2.36, 3.54, 4.72] # Water Air Heat Exchager steps for progressive working points
    def __init__(self,T_0=0):
        self.solid     = T_0
        self.oilHot    = T_0
        self.oilCold   = T_0
        self.waterHot  = T_0
        self.waterCold = T_0
        self.powerIN   = 0
        self.losses    = 0
        self.powerOUT  = 0
        self.water_air_trans = 0
        self.alarm     = False
        self.exchMode  = 0
        self.exchLag   = 0
        self.oilWater  = 0
        self.heatOut   = 0
    # Transformer heat losses as a function of output power, power factor and grid voltage
    def lossFunction(self,PF,V):
        self.losses  = polynomial_from_coeffs(self.powerOUT/PF/V/1000, [1.976, 2.181, 0.716, 0.086, 0.001])
        self.powerIN = self.powerOUT + self.losses
    # Function to chooses the cooling mode as a function of oil temperature. Presents hysteresis and a certain lag to avoid constant switching
    def exchCoeffFunc(self):
        self.exchLag  -= 1
        limitsUp=  [ 0, 80, 85, 90, 95]
        limitsDown=[ 0, 77, 82, 87, 92]
        if self.oilHot > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if self.oilHot > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (self.oilHot < limitsDown[self.exchMode]) & (self.exchLag<1) :
            for i in range(self.exchMode,0,-1):
                if self.oilHot < limitsDown[i]:
                    self.exchMode = i-1
        self.water_air_trans = self.exchCoeffs[self.exchMode]
    # Activate alarm if oil temperature excedes the limit
    def alarmFunc(self):
        if self.oilHot > self.oilHot_tempLimit:
            self.alarm = True
        else:
            self.alarm = False
    # Estimate of the max production that can be handled by the cooling system at a given ambient temperature
    def maxOut(self,Tamb):
        maxLoss = (self.oilHot_tempLimit - Tamb)*1.5
        return 1000*(math.sqrt(maxLoss)*0.79)
    # Calculation o the evolution of internal variables
    def timeStep(self,power,PF,V,Tamb):
        self.powerOUT = power
        self.lossFunction(PF,V)
        self.exchCoeffFunc()

        solid_oil     = (self.solid    - self.oilCold) * self.solid_oil_trans
        self.oilWater     = (self.oilHot   - self.waterCold) * self.oil_water_trans
        self.heatOut  = (self.waterHot - Tamb) * self.water_air_trans


        self.solid     += (self.losses * self.split - solid_oil) * config.dt  / self.solid_int
        self.oilCold   += (solid_oil - self.oilWater)    * config.dt  / self.oil_int
        self.waterCold += (self.oilWater - self.heatOut) * config.dt  / self.water_int

        self.oilHot     = self.oilCold   + solid_oil     / self.oilC
        self.waterHot   = self.waterCold + self.oilWater / self.waterC
        self.alarmFunc()
# Object which holds the behaviour parameters and the variables that define the state of a CONVERTER
class cv_component(object):
    solid_water_trans   = 2.50    #[kW/K] Circuits  ---> Water circuit
    solid_int           = 3680    #[kJ/K] Thermal inertia for the solid parts
    water_int           = 1440    #[kJ/K] Thermal inertia for the water in the circuit
    waterC              = 39.7    #[kW/K] Heat carryng capacity of the water current
    split               = 0.85    #       Estimate of the losses extracted by the liquid circuit
    waterCold_tempLimit = 50      #[C]    Alarm imposed for the cold water temperature
    exchCoeffs          = [0.25, 1.34, 2.67, 4.01, 5.35] # Water Air Heat Exchager steps for progressive working points

    def __init__(self,T_0=0):
        self.solid     = T_0
        self.waterHot  = T_0
        self.waterCold = T_0
        self.powerIN   = 0
        self.losses    = 0
        self.powerOUT  = 0
        self.water_air_trans = 0
        self.alarm     = False
        self.exchMode  = 0
        self.exchLag   = 0
        self.heatOut   = 0
        self.solidWater= 0
    # Converter heat losses as a function of converter output power, power factor and grid voltage
    def lossFunction(self,PF,V):
        self.losses  = polynomial_from_coeffs(self.powerOUT/PF/V/1000, [41.148, 12.625, 0.211])
        self.powerIN = self.powerOUT + self.losses
    # Function to chooses the cooling mode as a function of waterCold temperature. Presents hysteresis and a certain lag to avoid constant switching
    def exchCoeffFunc(self):
        self.exchLag  -= 1
        limitsUp=  [ 0, 31, 35, 39, 43]
        limitsDown=[ 0, 27, 31, 35, 39]
        if self.waterCold > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if self.waterCold > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (self.waterCold < limitsDown[self.exchMode]) & (self.exchLag<1):
            for i in range(self.exchMode,0,-1):
                if self.waterCold < limitsDown[i]:
                    self.exchMode = i-1
        self.water_air_trans = self.exchCoeffs[self.exchMode]
    # Activate alarm if cold water temperature excedes the limit
    def alarmFunc(self):
        if self.waterCold > self.waterCold_tempLimit:
            self.alarm = True
        else:
            self.alarm = False
    # Estimate of the max production that can be handled by the cooling system at a given ambient temperature
    def maxOut(self,Tamb):
        maxLoss = (self.waterCold_tempLimit - Tamb)*self.exchCoeffs[-1]
        return 1000*(maxLoss*0.06704/0.85-3.2)
    # Calculation o the evolution of internal variables
    def timeStep(self,power,PF,V,Tamb):
        self.powerOUT = power
        self.lossFunction(PF,V)
        self.exchCoeffFunc()

        self.solidWater = (self.solid    - self.waterCold) * self.solid_water_trans
        self.heatOut    = (self.waterHot - Tamb) * self.water_air_trans

        self.solid     += (self.losses * self.split - self.solidWater) * config.dt  / self.solid_int
        self.waterCold += (self.solidWater - self.heatOut) * config.dt  / self.water_int

        self.waterHot   = self.waterCold + self.solidWater / self.waterC
        self.alarmFunc()
# Object which holds the behaviour parameters and the variables that define the state of a GENERATOR
class gn_component(object):
    rotor_air_trans     = 0.70    #[kW/K]
    stator_air_trans    = 0.21    #[kW/K]
    stator_water_trans  = 0.8     #[kW/K]
    airIn_water_trans   = 3       #[kW/K]
    rotor_int           = 2000    #[kJ/K]
    stator_int          = 6200    #[kJ/K]
    water_int           = 864     #[kJ/K]
    airInC              = 5       #[kW/K]
    waterC              = 28.6    #[kW/K]
    split               = 0.95
    waterCold_tempLimit = 45
    exchCoeffs          = [0.25, 1.88, 3.75, 5.63, 7.50]

    def __init__(self,T_0=0):
        self.rotor     = T_0
        self.stator     = T_0
        self.airHot    = T_0
        self.airCold   = T_0
        self.waterHot  = T_0
        self.waterCold = T_0
        self.powerIN   = 0
        self.losses    = 0
        self.powerOUT  = 0
        self.water_air_trans = 0
        self.alarm     = False
        self.exchMode  = 0
        self.exchLag   = 0
        self.heatOut   = 0
    # Generator heat losses as a function of generator output power
    def lossFunction(self):
        #self.losses = polynomial_from_coeffs(self.powerOUT/1000, [25.052, 27.678, -0.816, -0.470, 0.050])
        self.losses = self.powerOUT*14.348/1000
        self.powerIN = self.powerOUT + self.losses
    # Function to chooses the cooling mode as a function of waterCold temperature. Presents hysteresis and a certain lag to avoid constant switching
    def exchCoeffFunc(self):
        self.exchLag  -= 1
        limitsUp=  [ 0, 35, 38, 41, 44]
        limitsDown=[ 0, 31, 34, 37, 40]
        if self.waterCold > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if self.waterCold > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (self.waterCold < limitsDown[self.exchMode]) & (self.exchLag<1) :
            for i in range(self.exchMode,0,-1):
                if self.waterCold < limitsDown[i]:
                    self.exchMode = i-1
        self.water_air_trans = self.exchCoeffs[self.exchMode]
    # Activate alarm if cold water temperature excedes the limit
    def alarmFunc(self):
        if self.waterCold > self.waterCold_tempLimit:
            self.alarm = True
        else:
            self.alarm = False
    # Estimate of the max production that can be handled by the cooling system at a given ambient temperature
    def maxOut(self,Tamb):
        maxLoss =  (self.waterCold_tempLimit - Tamb)*self.exchCoeffs[-1]
        return maxLoss*45-1000
    # Calculation o the evolution of internal variables
    def timeStep(self,power,Tamb):
        self.powerOUT = power
        self.lossFunction()
        self.exchCoeffFunc()

        rotor_air     = (self.rotor  - self.airCold)   * self.rotor_air_trans
        stator_air    = (self.stator - self.airCold)   * self.stator_air_trans
        stator_water  = (self.stator - self.waterCold) * self.stator_water_trans
        airIn_water   = (self.airHot - self.waterCold) * self.airIn_water_trans
        self.heatOut     = (self.waterHot - Tamb) * self.water_air_trans

        lossesRotor      = 0.4 * self.losses*self.split
        lossesStator     = self.losses*self.split - lossesRotor

        self.rotor     += (lossesRotor  - rotor_air) * config.dt  / self.rotor_int
        self.stator    += (lossesStator - stator_air - stator_water) * config.dt  / self.stator_int
        self.waterCold += (stator_water + stator_air + rotor_air - self.heatOut) * config.dt  / self.water_int

        self.waterHot = self.waterCold + (stator_water + stator_air + rotor_air)/self.waterC
        self.airHot   = self.waterCold + (stator_air   + rotor_air)/self.airIn_water_trans
        self.airCold  = self.airHot    - (stator_air   + rotor_air)/self.airInC
        self.alarmFunc()
# Object which holds the behaviour parameters and the variables that define the state of a GEARBOX
class gb_component(object):
    solid_oil_trans    = 13.0     #[kW/K] Gears ---> Oil bath
    oil_water_trans    = 12.205   #[kW/K] Oil Water Heat Exchager
    solid_int          = 44200    #[kJ/K] Thermal inertia for the solid parts
    oil_int            = 4260     #[kJ/K] Thermal inertia for the oil bath
    water_int          = 1530     #[kJ/K] Thermal inertia for the water in the circuit
    oilC               = 14.135   #[kW/K] Heat carryng capacity of the oil current
    waterC             = 26.316   #[kW/K] Heat carryng capacity of the water current
    split              = 0.95     #       Estimate of the losses extracted by the liquid circuit
    oilCold_tempLimit  = 46       #[C]    Alarm imposed for the oilCold temperature
    exchCoeffs         = [0.25, 1.97, 3.94, 5.91, 7.88]
    def __init__(self,T_0=0):
        self.solid     = T_0
        self.oilHot    = T_0
        self.oilCold   = T_0
        self.waterHot  = T_0
        self.waterCold = T_0
        self.powerIN   = 0
        self.losses    = 0
        self.powerOUT  = 0
        self.water_air_trans = 0
        self.alarm     = False
        self.exchMode  = 0
        self.exchLag   = 0
        self.heatOut   = 0
        self.oilWater  = 0
    # Gearbox heat losses as a function of gearbox output power
    def lossFunction(self):
        eff=np.interp(self.powerOUT/1000, [0.0,   0.9,    1.8,    2.97,   3.6,    4.68,   5.4,    6.3,    7.2,    7.65,   9],
                                             [0.849, 0.9599, 0.9713, 0.9801, 0.9818, 0.9845, 0.9858, 0.9868, 0.9878, 0.9882, 0.989])
        self.losses  = (20*self.powerOUT/9000 + self.powerOUT*( 1 - eff )/eff)
        self.powerIN = self.powerOUT + self.losses
    # Function to chooses the cooling mode as a function of waterCold temperature. Presents hysteresis and a certain lag to avoid constant switching
    def exchCoeffFunc(self):
        self.exchLag  -= 1
        limitsUp=  [ 0, 39, 41, 43, 45]
        limitsDown=[ 0, 37, 39, 41, 43]
        if self.oilCold > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if self.oilCold > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (self.oilCold < limitsDown[self.exchMode]) & (self.exchLag<1) :
            for i in range(self.exchMode,0,-1):
                if self.oilCold < limitsDown[i]:
                    self.exchMode = i-1
        self.water_air_trans = self.exchCoeffs[self.exchMode]
    # Activate alarm if oilCold temperature excedes the limit
    def alarmFunc(self):
        if self.oilCold > self.oilCold_tempLimit:
            self.alarm = True
        else:
            self.alarm = False
    # Estimate of the max production that can be handled by the cooling system at a given ambient temperature
    def maxOut(self,Tamb):
        maxLoss = (self.oilCold_tempLimit - Tamb)*self.exchCoeffs[-1]
        return maxLoss/0.02
    # Calculation o the evolution of internal variables
    def timeStep(self,power,Tamb):
        self.powerOUT = power
        self.lossFunction()
        self.exchCoeffFunc()

        solid_oil     = (self.solid    - self.oilCold) * self.solid_oil_trans
        self.oilWater = (self.oilHot   - self.waterCold) * self.oil_water_trans
        self.heatOut  = (self.waterHot - Tamb) * self.water_air_trans

        self.solid     += (self.losses * self.split - solid_oil) * config.dt  / self.solid_int
        self.oilCold   += (solid_oil - self.oilWater)    * config.dt  / self.oil_int
        self.waterCold += (self.oilWater - self.heatOut) * config.dt  / self.water_int

        self.oilHot     = self.oilCold   + solid_oil / self.oilC
        self.waterHot   = self.waterCold + self.oilWater / self.waterC
        self.alarmFunc()
# Object which holds the behaviour parameters and the variables that define the state of a NACELLE
class nac_component(object):
    air_int            = 400     #[kJ/K] Thermal inertia for the oil bath
    airC               = 10      #[kW/K] Heat carryng capacity of the water current
    airCold_Limit      = 38
    exchCoeffs         = [0.1, 1, 1.5, 2, 2.556]
    cover_trans        = [0.1, 0.25, 0.5, 1, 1.5]  #[kW/K]

    def __init__(self,T_0=0):
        self.airHot        = T_0
        self.airMiddle     = T_0
        self.airCold       = T_0
        self.coverOut      = 0
        self.componentsIn  = 0
        self.exchOut       = 0
        self.alarm         = False
        self.exchMode      = 0
        self.exchLag       = 0

    # Function to chooses the cooling mode as a function of waterCold temperature. Presents hysteresis and a certain lag to avoid constant switching
    def exchCoeffFunc(self):
        self.exchLag  -= 1
        limitsUp=  [ 0, 29, 32, 35, 39]
        limitsDown=[ 0, 27, 30, 33, 36]
        if self.airMiddle > limitsUp[self.exchMode]:
            for i in range(self.exchMode,len(limitsUp)):
                if self.airMiddle > limitsUp[i]:
                    self.exchMode = i
                    self.exchLag  = config.exchLag
        elif (self.airMiddle < limitsDown[self.exchMode]) & (self.exchLag<1) :
            for i in range(self.exchMode,0,-1):
                if self.airMiddle < limitsDown[i]:
                    self.exchMode = i-1
        #self.water_air_trans = self.exchCoeffs[self.exchMode]
    # Activate alarm if airCold temperature excedes the limit
    def alarmFunc(self):
        if self.airCold > self.airCold_Limit:
            self.alarm = True
        else:
            self.alarm = False
    def nacelleExhangerFunction (self, airHot,Tamb):
        self.exchCoeffFunc()
        return (airHot-Tamb)*self.exchCoeffs[self.exchMode]
    # Calculation o the evolution of internal variables
    def timeStep(self, ge_contribution, gb_contribution, Tamb):
        self.componentsIn = ge_contribution + gb_contribution + 5   # the extra bit is for the other components in the NACELLE

        self.coverOut  = (self.airHot   - Tamb) * self.cover_trans[self.exchMode]
        self.airMiddle = self.airHot - self.coverOut / self.airC
        self.exchOut   = self.nacelleExhangerFunction(self.airMiddle, Tamb)

        self.airCold   += (self.componentsIn - self.coverOut - self.exchOut) * config.dt  / self.air_int

        self.airHot     = self.airCold   + self.componentsIn / self.airC
        self.alarmFunc()
# Object which holds the behaviour parameters and the variables that define the state of a AIRMASS in tower and NACELLE
class air_volume(object):
    def __init__(self, nodesfile, bondsfile):
        self.someVariables = 0
class air_volume_GBM(object):
    # cover_trans        = [0.1, 0.25, 0.5, 1, 1.5]  #[kW/K]
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


        self.model.pressure = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.NonNegativeReals,initialize =1)


        self.model.exterior = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.Reals,initialize =1)

        self.temperature    = pyoenv.Var(self.model.node_set,
                                         domain=pyoenv.Reals,initialize =1)


        # Create objective
        def obj_rule(model):
            dummy = [((self.model.pressure[i]- self.model.pressure[j] - self.bond_data.ix[(i,j),'dropCoeff']*self.model.flow[(i,j)]**2) if not self.bond_data.ix[(i,j),'Fan'] else 0) for (i,j) in self.model.bond_set]
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
        results = solver.solve(self.model, tee=False, keepfiles=False )#, options_string="mip_tolerances_integrality=1e-9 mip_tolerances_mipgap=0")

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
        s = ' %-50s  %-5.2f'

        print('\n %-50s  %-5s' % ('Bond', 'Flow'))
        for i in self.model.flow:
            print(s % (i, self.model.flow[i].value))

        print('\n %-50s  %-5s' % ('Node', 'Exterior'))
        for i in self.model.exterior:
            print(s % (i,self.model.exterior[i].value))

        print('\n %-50s  %-5s' % ('Node', 'Exterior'))
        for i in self.model.exterior:
            print(s %(i,self.model.pressure[i].value))
