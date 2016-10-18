
def hysteresisFunc(T, Tup, Tdown, h_pre):
    length = len(Tup)
    h = h_pre
    for i in range(h_pre,1,-1):
        if T<Tdown[i]:
            return i-1

    for i in range(h_pre+1,length):
        if T>Tup[i]:
            return i
    return h

def tr_CoeffFunc(tr_oilHot, tr_exch_coeff_pre): #[kW/K]
    tr_LimitsUp=  [-273, 0, 80, 85, 90, 95]
    tr_LimitsDown=[-273, 0, 77, 82, 87, 92]
    return hysteresisFunc(tr_oilHot, tr_LimitsUp, tr_LimitsDown, tr_exch_coeff_pre)

def cv_CoeffFunc(cv_waterCold,cv_exch_coeff_pre): #[kW/K]
    cv_LimitsUp=  [-273, 0, 31, 35, 39, 43]
    cv_LimitsDown=[-273, 0, 27, 31, 35, 39]
    return hysteresisFunc(cv_waterCold, cv_LimitsUp, cv_LimitsDown, cv_exch_coeff_pre)


def gn_CoeffFunc(gn_waterCold, gn_exch_coeff_pre): #[kW/K]
    gn_LimitsUp=  [-273, 0, 35, 38, 41, 44]
    gn_LimitsDown=[-273, 0, 31, 34, 37, 40]
    return hysteresisFunc(gn_waterCold, gn_LimitsUp, gn_LimitsDown, gn_exch_coeff_pre)

def gb_CoeffFunc(gb_oilCold,gb_exch_coeff_pre): #[kW/K]
    gb_LimitsUp   = [-273, 0, 39, 41, 43, 45]
    gb_LimitsDown = [-273, 0, 37, 39, 41, 43]
    return hysteresisFunc(gb_oilCold, gb_LimitsUp, gb_LimitsDown, gb_exch_coeff_pre)

class ComponentsState(object):

    tr_solid_oil_trans    = 5.333   #[kW/K]
    tr_oil_water_trans    = 2.491   #[kW/K]
    tr_solid_int          = 4370    #[kJ/K]
    tr_oil_int            = 8650    #[kJ/K]
    tr_water_int          = 616     #[kJ/K]
    tr_oilC               = 9.12    #[kW/K]
    tr_waterC             = 19.5    #[kW/K]

    cv_solid_water_trans  = 2.50    #[kW/K]
    cv_solid_int          = 3680    #[kJ/K]
    cv_water_int          = 1440    #[kJ/K]
    cv_waterC             = 39.7    #[kW/K]

    gn_rotor_air_trans    = 2       #[kW/K]
    gn_stator_air_trans   = 1       #[kW/K]
    gn_stator_water_trans = 2       #[kW/K]
    gn_airIn_water_trans  = 3       #[kW/K]
    gn_rotor_int          = 6370    #[kJ/K]
    gn_stator_int         = 2450    #[kJ/K]
    gn_water_int          = 864     #[kJ/K]
    gn_airInC             = 5       #[kW/K]
    gn_waterC             = 29.376  #[kW/K]

    gb_solid_oil_trans    = 13.0    #[kW/K]
    gb_oil_water_trans    = 12.205  #[kW/K]
    gb_solid_int          = 44200   #[kJ/K]
    gb_oil_int            = 4260    #[kJ/K]
    gb_water_int          = 1530    #[kJ/K]
    gb_oilC               = 14.135  #[kW/K]
    gb_waterC             = 26.316  #[kW/K]

    tr_split              = 0.95
    cv_split              = 0.85
    gn_split              = 0.95
    gb_split              = 0.95


    def __init__(self,T0):

        self.trafo          = [T0,T0,T0,T0,T0]          # solidT oilHot oilCold waterHot waterCold
        self.converter      = [T0,T0,T0]      # solidT                waterHot waterCold
        self.generator      = [T0,T0,T0,T0,T0,T0]      # stator rotor  airHot  airCold  waterHot waterCold
        self.gearbox        = [T0,T0,T0,T0,T0]        # solidT oilHot oilCold waterHot waterCold
        self.exchangeCoeffs = [0,0,0,0] # tranfo converter generator gearbox
        self.alarms         = [0,0,0,0]

    def inputDetails(self, trafo_IN, converter_IN, generator_IN, gearbox_IN, exchangeCoeffs_IN, alarms_IN):

        self.trafo          = trafo_IN          # solidT oilHot oilCold waterHot waterCold
        self.converter      = converter_IN      # solidT                waterHot waterCold
        self.generator      = generator_IN      # stator rotor  airHot  airCold  waterHot waterCold
        self.gearbox        = gearbox_IN        # solidT oilHot oilCold waterHot waterCold
        self.exchangeCoeffs = exchangeCoeffs_IN # tranfo converter generator gearbox
        self.alarms         = alarms_IN

    def timeStep(self, dt, trafoLosses, convLosses, generLosses, gearbLosses, airT, powerFactor, gridVoltage):

        outputComponentStep=ComponentsState(0)

        trafo_OUT          = [0,0,0,0,0]
        converter_OUT      = [0,0,0]
        generator_OUT      = [0,0,0,0,0,0]
        gearbox_OUT        = [0,0,0,0,0]
        exchangeCoeffs_OUT = [0,0,0,0]
        alarms_OUT         = [0,0,0,0]

        exchangeCoeffs_OUT[0] = int(tr_CoeffFunc(self.trafo[1],self.exchangeCoeffs[0]))
        tr_water_air_trans = [0 ,0.25, 1.18, 2.36, 3.54, 4.72][exchangeCoeffs_OUT[0]]#[kW/K]

        exchangeCoeffs_OUT[1] = int(cv_CoeffFunc(self.converter[2],self.exchangeCoeffs[1]))
        cv_water_air_trans = [0 ,0.25, 1.34, 2.67, 4.01, 5.35][exchangeCoeffs_OUT[1]]#[kW/K]

        exchangeCoeffs_OUT[2] = int(gn_CoeffFunc(self.generator[5],self.exchangeCoeffs[2]))
        gn_water_air_trans = [0 ,0.25, 1.88, 3.75, 5.63, 7.50][exchangeCoeffs_OUT[2]]#[kW/K]

        exchangeCoeffs_OUT[3] = int(gb_CoeffFunc(self.gearbox[2],self.exchangeCoeffs[3]))
        gb_water_air_trans = [0 ,0.25, 1.97, 3.94, 5.91, 7.88][exchangeCoeffs_OUT[3]]#[kW/K]

        #----------

        tr_solid_oil     = (self.trafo[0]-self.trafo[2])*self.tr_solid_oil_trans
        tr_oil_water     = (self.trafo[1]-self.trafo[4])*self.tr_oil_water_trans
        tr_water_air     = (self.trafo[3]-airT)*tr_water_air_trans

        trafo_OUT[0]     = self.trafo[0]+(trafoLosses*self.tr_split-tr_solid_oil)*dt/self.tr_solid_int
        trafo_OUT[2]     = self.trafo[2]+(tr_solid_oil-tr_oil_water)*dt/self.tr_oil_int
        trafo_OUT[4]     = self.trafo[4]+(tr_oil_water-tr_water_air)*dt/self.tr_water_int

        trafo_OUT[1]     = trafo_OUT[2]+tr_solid_oil/self.tr_oilC
        trafo_OUT[3]     = trafo_OUT[4]+tr_oil_water/self.tr_waterC

        #----------

        cv_solid_water   = (self.converter[0]-self.converter[2])*self.cv_solid_water_trans
        cv_water_air     = (self.converter[1]-airT)*cv_water_air_trans

        converter_OUT[0] = self.converter[0] + (convLosses*self.cv_split-cv_solid_water)*dt/self.cv_solid_int
        converter_OUT[2] = self.converter[2] + (cv_solid_water-cv_water_air)*dt/self.cv_water_int
        converter_OUT[1] = converter_OUT[2] + cv_solid_water/self.cv_waterC

        #----------

        gn_rotor_air     = (self.generator[1] - self.generator[3]) * self.gn_rotor_air_trans
        gn_stator_air    = (self.generator[0] - self.generator[3]) * self.gn_stator_air_trans
        gn_stator_water  = (self.generator[0] - self.generator[5]) * self.gn_stator_air_trans
        gn_airIn_water   = (self.generator[2] - self.generator[5]) * self.gn_airIn_water_trans
        gn_water_air     = (self.generator[4] - airT)  * gn_water_air_trans

        generLosses      = generLosses * self.gn_split
        lossesRotor      = 0.4 * generLosses
        lossesStator     = generLosses - lossesRotor

        generator_OUT[1] = self.generator[1]+(lossesRotor - gn_rotor_air) * dt / self.gn_rotor_int
        generator_OUT[0] = self.generator[0]+(lossesStator - gn_stator_air - gn_stator_water) * dt / self.gn_stator_int
        generator_OUT[5] = self.generator[5]+(gn_stator_water + gn_stator_air + gn_rotor_air - gn_water_air) * dt / self.gn_water_int

        generator_OUT[4] = generator_OUT[5]+(gn_stator_water + gn_stator_air + gn_rotor_air)/self.gn_waterC
        generator_OUT[2] = generator_OUT[5]+(gn_stator_air + gn_rotor_air)/self.gn_airIn_water_trans
        generator_OUT[3] = generator_OUT[2]-(gn_stator_air + gn_rotor_air)/self.gn_airInC

        #----------

        gb_solid_oil     = (self.gearbox[0]-self.gearbox[2])*self.gb_solid_oil_trans
        gb_oil_water     = (self.gearbox[1]-self.gearbox[4])*self.gb_oil_water_trans
        gb_water_air     = (self.gearbox[3]-airT)*gb_water_air_trans

        gearbox_OUT[0]   = self.gearbox[0]+(gearbLosses*self.gb_split-gb_solid_oil)*dt/self.gb_solid_int
        gearbox_OUT[2]   = self.gearbox[2]+(gb_solid_oil-gb_oil_water)*dt/self.gb_oil_int
        gearbox_OUT[4]   = self.gearbox[4]+(gb_oil_water-gb_water_air)*dt/self.gb_water_int

        gearbox_OUT[1]   = gearbox_OUT[2]+gb_solid_oil/self.gb_oilC
        gearbox_OUT[3]   = gearbox_OUT[4]+gb_oil_water/self.gb_waterC

        #----------
        if trafo_OUT[1] > 120:
            alarms_OUT[0]=1

        if converter_OUT[2] > 50:
            alarms_OUT[1]=1

        if generator_OUT[5] > 45:
            alarms_OUT[2]=1

        if gearbox_OUT[2] > 45:
            alarms_OUT[3]=1

        outputComponentStep.inputDetails(trafo_OUT, converter_OUT, generator_OUT, gearbox_OUT, exchangeCoeffs_OUT,alarms_OUT)

        return outputComponentStep
