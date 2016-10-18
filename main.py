import time
import config

from thermal_inertia_tools import *
from graphTools            import *
from machineBehaviour      import *

start_time                = time.time()
timeToSimulate            = datetime.timedelta(days = 0.01)              # For how loong should the simulation run
config.powerCurve         = loadPowerCurve(9000)                       # Load a power curve limmeiting at the max power
[winds, temperatures]     = loadWindTemperatureSeries(testing = False) # Load wind and temperature time series
[powerFactor,gridVoltage] = [0.925, 0.9]                               # Default Grid conditions, they might be modified because of derating
stateSeries               = [machineState(temperatures[0])]            # All components start at the same temperature as the ambient
#stateSeries[0].removeTempLimits()

# Runs for the stipulated time while ambient data is available
i = 0
while ((stateSeries[-1].time - stateSeries[0].time) < timeToSimulate) & bool(winds) & bool(temperatures):
    # Appends a new timestep to the series
    stateSeries.append(stateSeries[-1].machineTimeStep(winds[i], powerFactor, gridVoltage, temperatures[i]))
    i += 1
    if i%1000 == 0: print stateSeries[-1].time
    # Removes the first element of the ambient conditions list

print('Expected AEP         :   %s MW h' % (sum(item.potential for item in stateSeries)*525600/len(stateSeries)/1000/60))
print('Expected AEP derated :   %s MW h' % (sum(item.power     for item in stateSeries)*525600/len(stateSeries)/1000/60))
print('Evolution Calculation--- %s seconds ---' % (time.time() - start_time))

#outputRequestedGraphs(stateSeries)                      # Graphs related with component internal temperatures and ambient conditions
#powerVsPotentialgraph(stateSeries)                      # Graph comparing potential and derated production
#graphNacelle(stateSeries)
print("Graphing--- %s seconds ---" % (time.time() - start_time))
