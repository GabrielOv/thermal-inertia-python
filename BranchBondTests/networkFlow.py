from pyomo.core import *

model = AbstractModel()

model.nodes        = Set()
model.bonds        = Set(within = model.nodes*model.nodes)
model.source       = Param(model.nodes)
model.sink         = Param(model.nodes)
model.minExterior  = Param(model.nodes)
model.maxExterior  = Param(model.nodes)
model.dropCoeff    = Param(model.bonds)
model.minForced    = Param(model.bonds)
model.maxForced    = Param(model.bonds)
model.flow         = Var(model.bonds, within = NonNegativeReals)
model.pressure     = Var(model.nodes, within = NonNegativeReals)
model.exterior     = Var(model.nodes, within = NonNegativeReals)

# def pDropRule(model,i,j):
#     pFrom  = model.pressure[i]
#     pTo    = model.pressure[j]
#     pDrop  = model.dropCoeff[i,j]*model.flow[i,j]
#     return pFrom-pDrop-pTo
# model.costTotal = Objective(rule = pDropRule)
 # Create objective
def obj_rule(model):
    return sum( model.dropCoeff[e]*model.flow[e]**2 for e in model.bonds)
model.OBJ = Objective(rule=obj_rule, sense=minimize)

def forcedFlowRule(model,i,j):
    return (model.minForced[i,j], model.flow[i,j], model.maxForced[i,j])
model.forcedFlow = Constraint(model.bonds, rule = forcedFlowRule)

def opennesRule(model, i):
    return (model.minExterior[i], model.exterior[i], model.maxExterior[i])
model.loadOnRoad = Constraint(model.nodes, rule = opennesRule)

def continuityEq(model, nn):

    amountIn  = sum(model.flow[i,j] for (i,j) in model.bonds if j == nn)
    amountOut = sum(model.flow[i,j] for (i,j) in model.bonds if i == nn)

    inbound  = amountIn  + model.source[nn]
    outbound = amountOut + model.sink[nn] + model.exterior[nn]

    return inbound == outbound
model.supplyDemand = Constraint(model.nodes, rule=continuityEq)

def continuityEq(model, nn):

    amountIn  = sum(model.flow[i,j] for (i,j) in model.bonds if j == nn)
    amountOut = sum(model.flow[i,j] for (i,j) in model.bonds if i == nn)

    inbound  = amountIn  + model.source[nn]
    outbound = amountOut + model.sink[nn] + model.exterior[nn]

    return inbound == outbound
model.supplyDemand = Constraint(model.nodes, rule=continuityEq)
