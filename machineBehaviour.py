import copy
import time
import math
import numpy
import datetime

from thermal_inertia_tools import *
import config

# Object that represents the wind turbine generator an a certain time
class machineState(object):
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

    # Returns a new instance of the machine state evolved for the ambient conditions given
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
        return newTime
    # Returns interpolation of power produtcion given a  wind speed
    def powerFunction(self):
        return  numpy.interp(self.wind, config.powerCurve[0], config.powerCurve[1])
    # Returns a vector with the alarm state for all components
    def getAlarms(self):
        return [self.transformer.alarm, self.converter.alarm, self.generator.alarm, self.gearbox.alarm]
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
        self.losses = polynomial_from_coeffs(self.powerOUT/1000, [25.052, 27.678, -0.816, -0.470, 0.050])
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
        eff=numpy.interp(self.powerOUT/1000, [0.4, 2.4, 7.2, 10],[0.972, 0.972, 0.985,0.985])
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
    cover_trans        = 1.5     #[kW/K] Gears ---> Oil bath
    air_int            = 400     #[kJ/K] Thermal inertia for the oil bath
    airC               = 10      #[kW/K] Heat carryng capacity of the water current
    airCold_Limit      = 38
    exchCoeffs         = [0.1, 1, 1.5, 2, 2.57]

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

        self.coverOut  = (self.airHot   - Tamb) * self.cover_trans
        self.airMiddle = self.airHot - self.coverOut / self.airC
        self.exchOut   = self.nacelleExhangerFunction(self.airMiddle, Tamb)

        self.airCold   += (self.componentsIn - self.coverOut - self.exchOut) * config.dt  / self.air_int

        self.airHot     = self.airCold   + self.componentsIn / self.airC
        self.alarmFunc()
