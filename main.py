#!/usr/bin/env python

import time
import config
import pickle

from thermal_inertia_tools import *
from graphTools            import *
from machineBehaviour      import *

print( "Loading data series, power curve and starting conditions")
start_time                = time.time()
timeToSimulate            = datetime.timedelta(days = 20)             # For how loong should the simulation run
config.powerCurve         = loadPowerCurve(9000)                       # Load a power curve limmeiting at the max power
[winds, temperatures]     = loadWindTemperatureSeries(testing = False) # Load wind and temperature time series
[powerFactor,gridVoltage] = [0.9, 0.925]                                 # Default Grid conditions, they might be modified because of derating
stateSeries               = [machineState(temperatures[0])]            # All components start at the same temperature as the ambient

print("Simulation will calculate %i days or until ambient data runs out" % timeToSimulate.days)
i = 0
calc_begining_time          = time.time()
while ((stateSeries[-1].time - stateSeries[0].time) < timeToSimulate) & (i< min(len(winds), len(temperatures))):
    # Appends a new timestep to the series
    stepCounter = machineState.machineTimeStep.called
    stateSeries.append(stateSeries[-1].machineTimeStep(winds[stepCounter], powerFactor, gridVoltage, temperatures[stepCounter]))

    if stepCounter%14400 == 0: print( (stateSeries[-1].time - stateSeries[0].time).days, "days completed in ", int(time.time()-calc_begining_time), "seconds")


calculateAEP(stateSeries)
calc_end_time        = time.time()
print('Calculation took     :   %i seconds'  % (calc_end_time - calc_begining_time))

outputRequestedGraphs(stateSeries)                      # Graphs related with component internal temperatures and ambient conditions
powerVsPotentialgraph(stateSeries)                      # Graph comparing potential and derated production

print('Building graphs took :   %i seconds'  % (time.time() - calc_end_time))
print( "--------- DONE !!! ---------")

output = open('data.pkl', 'wb')
pickle.dump(stateSeries, output)
output.close()
