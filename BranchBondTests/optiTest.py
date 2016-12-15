from pyomo.core import *

model = AbstractModel()

model.places   = Set()
model.routes   = Set(within=model.places*model.places)
model.supply   = Param(model.places)
model.demand   = Param(model.places)
model.pCoeff   = Param(model.routes)
model.minFlow  = Param(model.routes)
model.maxFlow  = Param(model.routes)
model.minP     = Param(model.places)
model.maxP     = Param(model.places)
model.flow     = Var(model.routes, within=NonNegativeReals)
model.pressure = Var(model.places, within=NonNegativeReals)

def flowBounds(model, i, j):
    return (model.minFlow[i,j], model.flow[i,j], model.maxFlow[i,j])

model.boundFlow = Constraint(model.routes, rule=flowBounds)

def pressureBounds(model, i):
    return (model.minP[i], model.pressure[i], model.maxP[i])

model.boundPressure = Constraint(model.places, rule=pressureBounds)

def continuityRule(model, nn):

    flowIn  = sum(model.flow[i,j] for (i,j) in model.routes if j == nn)
    flowOut = sum(model.flow[i,j] for (i,j) in model.routes if i == nn)

    input  = flowIn  + model.supply[nn]
    output = flowOut + model.demand[nn]

    return input == output

model.continuity = Constraint(model.places, rule=continuityRule)

def momentumRule(model):    
    return sum(pow(model.pressure[i] - model.pressure[j] - model.pCoeff[i,j]*model.flow[i,j],2) for (i,j) in model.routes )

model.momentum = Objective(rule=momentumRule)



