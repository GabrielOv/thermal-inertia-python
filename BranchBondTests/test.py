from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr

import numpy as np
i=4
j=5

GraphBondMatrix= np.array([[-1, 0, 0, 1, 1],
                            [ 1,-1,-1, 0, 0],
                            [ 0, 1, 0,-1, 0],
                            [ 0, 0, 1, 0,-1]])

knownMflow      = np.array([[ 0, 0, 0, 2, 2]])
exterMflow      = np.array([[ 5, 0, 0, 0]])
knownP          = np.array([[ 0, 0, 1, 1]])
DropCoeffs      = np.array([[ 1, 1, 4, 0, 0]])
# GraphBondMatrix = np.array([[-1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
#                               [ 1,-1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 1,-1, 0, 0, 0, 0, 0, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 1,-1, 1, 0, 0, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0,-1,-1, 1,-1, 1, 0, 0, 0, 0,-1,-1, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,-1 0,-1,-1, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0,-1, 0, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,-1, 0, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0,-1, 0, 0],
#                               [ 0, 0, 0, 0, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1,-1],
#                               [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,-1, 0],
#                               ])
#Mexternals      = np.array([ 0, 0, 0, -0.175, 0, 0.807, 0, -0.605, 0, 0, 0, 0, 0, 0, 0])
#PdropCoeffs     = [ 0, 0, 0, -0.175, 0, 0.807, 0, -0.605, 0, 0, 0, 0, 0, 0, 0]
#Pdrop           = np.array([ 0, 0, 0, -0.175, 0, 0.807, 0, -0.605, 0, 0, 0, 0, 0, 0, 0])
# x = lsqr(GraphBondMatrix, -exterMflowPrime)[0].T + knownMflow
# padding1= np.zeros((i,i))
# padding2= np.zeros((j,j))
# A = np.concatenate((GraphBondMatrixB,padding2),axis=0)
# B = np.concatenate((padding1,GraphBondMatrixB.T),axis=0)
# GraphBondMatrix= np.concatenate((A,B),axis=1)
GraphBondMatrixM = GraphBondMatrix
GraphBondMatrixM[:,3]=0
GraphBondMatrixM[:,4]=0
GraphBondMatrixM[2,:]=0
GraphBondMatrixM[3,:]=0
GraphBondMatrixP = GraphBondMatrix.T
GraphBondMatrixP[:,2]=0
GraphBondMatrixP[:,3]=0
GraphBondMatrixP[3,:]=0
GraphBondMatrixP[4,:]=0
print GraphBondMatrixM
print GraphBondMatrixP

exterMflowPrime = exterMflow.T+np.dot(GraphBondMatrix,knownMflow.T)
MFlows = lsqr(GraphBondMatrixM, -exterMflowPrime)[0].T + knownMflow
PDrops = np.multiply(np.multiply(MFlows,MFlows),DropCoeffs)
PNodes =lsqr(GraphBondMatrixP, -PDrops)[0].T + knownP
# print exterMflowPrime
print MFlows
print PDrops
print PNodes


import pyOpt

def objfunc(x):

    f = -x[0]*x[1]*x[2]
    g = [0.0]*2
    g[0] = x[0] + 2.*x[1] + 2.*x[2] - 72.0
    g[1] = -x[0] - 2.*x[1] - 2.*x[2]

    fail = 0
    return f,g, fail

opt_prob = pyOpt.Optimization('TP37 Constrained Problem',objfunc)
opt_prob.addObj('f')

opt_prob.addVar('x1','c',lower=0.0,upper=42.0,value=10.0)
opt_prob.addVar('x2','c',lower=0.0,upper=42.0,value=10.0)
opt_prob.addVar('x3','c',lower=0.0,upper=42.0,value=10.0)
opt_prob.addConGroup('g',2,'i')

print opt_prob

slsqp = pyOpt.SLSQP()
slsqp.setOption('IPRINT', -1)
[fstr, xstr, inform] = slsqp(opt_prob,sens_type='FD')
#
# print opt_prob.solution(0)
