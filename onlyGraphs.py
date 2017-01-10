#!/usr/bin/env python

import time
import config
import pickle

from thermal_inertia_tools import *
from graphTools            import *
from machineBehaviour      import *

print( "Loading data series, power curve and starting conditions")
start_time                = time.time()

pkl_file = open('data.pkl', 'rb')
stateSeries  = pickle.load(pkl_file)
pkl_file.close()

calculateAEP(stateSeries)
calc_end_time        = time.time()

outputRequestedGraphs(stateSeries)                      # Graphs related with component internal temperatures and ambient conditions
powerVsPotentialgraph(stateSeries)                      # Graph comparing potential and derated production

print('Building graphs took :   %i seconds'  % (time.time() - calc_end_time))
print( "--------- DONE !!! ---------")
