import csv
import math
import datetime
import numpy as np

import config

# Reads the power curve present in the folder and limits it to the rated power expressed in kW
def loadPowerCurve( ratedPower ):

    powerCurve=[[],[]]

    with open('PowerCurve.csv', 'rb') as csvfile:
        powerCurveReader = csv.reader(csvfile, delimiter=';', quotechar='|')
        for row in powerCurveReader:
            powerCurve[0].append(float(row[0]))
            if float(row[1])<= ratedPower :
                powerCurve[1].append(float(row[1]))
            else:
                powerCurve[1].append(ratedPower)
    return powerCurve
# Reads the wind and temperature dataset and returns them in separate lists for dummy conditions testing = true
def loadWindTemperatureSeries( testing = False  ):
    temperatureSeries=[]
    windSeries=[]
    if testing:  # Returns constant temperature and a step function on wind
        temperatureSeries = [config.dummyTamb]*config.dataSetLength
        windSeries        = [config.dummyWind]*(config.dataSetLength/2)
        windSeries.extend([0]*(config.dataSetLength/2))
    else:       # Returns the time series contained in the csv files specified
        with open('TemperatureBMHV.csv', 'rb') as csvfile:
            temperatureReader = csv.reader(csvfile, delimiter=';', quotechar='|')
            for row in temperatureReader:
                temperatureSeries.extend([float(row[0])]*config.strechFactor)
        with open('WindBMHV.csv', 'rb') as csvfile:
            windReader = csv.reader(csvfile, delimiter=';', quotechar='|')
            for row in windReader:
                windSeries.extend([float(row[0])]*config.strechFactor)
    return [windSeries, temperatureSeries]
# Auxiliary function for the classical  y = C0 + C1*x + C2*x^2 + C3*x^3 ...
def polynomial_from_coeffs( x, coeffs ):
    y=0
    for i in range(len(coeffs)):
        y = y + coeffs[i]*x**i
    return y
#
def calculateAEP(stateSeries):
    print('Expected AEP         :   %i MW h' % (sum(item.potential for item in stateSeries)*525600/len(stateSeries)/1000/60))
    print('Expected AEP derated :   %i MW h' % (sum(item.power     for item in stateSeries)*525600/len(stateSeries)/1000/60))
class countcalls(object):
   "Decorator that keeps track of the number of times a function is called."

   __instances = {}

   def __init__(self, f):
      self.__f = f
      self.__numcalls = 0
      countcalls.__instances[f] = self

   def __call__(self, *args, **kwargs):
      self.__numcalls += 1
      return self.__f(*args, **kwargs)

   def count(self):
      "Return the number of times the function f was called."
      return countcalls.__instances[self.__f].__numcalls

   @staticmethod
   def counts():
      "Return a dict of {function: # of calls} for all registered functions."
      return dict([(f.__name__, countcalls.__instances[f].__numcalls) for f in countcalls.__instances])
