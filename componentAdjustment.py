from plotly.offline import init_notebook_mode, iplot
import plotly.graph_objs as go
from machineBehaviour_2 import *



def tr_adjust(solid_oil_trans, oil_water_trans, solid_int, oil_int,water_int,oilC,waterC,PF,V,wind,temp):
    temperature = temp
    wind        = wind
    [powerFactor,gridVoltage] = [PF, V]

    initialState = machineState(temperature)
    initialState.transformer.solid_oil_trans = solid_oil_trans
    initialState.transformer.oil_water_trans = oil_water_trans
    initialState.transformer.solid_int = solid_int
    initialState.transformer.oil_int = oil_int
    initialState.transformer.water_int = water_int
    initialState.transformer.oilC = oilC
    initialState.transformer.waterC = waterC

    initialState.transformer.exchCoeffs = [4.72, 4.72, 4.72, 4.72, 4.72]
    initialState.removeTempLimits()

    stateSeries  = [initialState]

    for i in range(300):
        stateSeries.append(stateSeries[-1].machineTimeStep(wind, powerFactor, gridVoltage, temperature))
        stateSeries[-1].transformer.waterCold   = temp

    tr_solid     = [item.transformer.solid for item in stateSeries]
    tr_oilHot    = [item.transformer.oilHot for item in stateSeries]
    tr_waterHot  = [item.transformer.waterHot for item in stateSeries]
    tr_waterCold = [item.transformer.waterCold for item in stateSeries]
    losses       = [item.transformer.losses for item in stateSeries]
    extracted    = [item.transformer.oilWater for item in stateSeries]
    times        = [item.time  for item in stateSeries]

    solidTrace    = go.Scatter(x=times, y=tr_solid,     name='Windings T',   line = dict(color = 'lime' ,width = 1,dash = 'dot'))
    oilHotTrace   = go.Scatter(x=times, y=tr_oilHot,    name='Oil Hot T',    line = dict(color = 'orangered'))
    waterHotTrace = go.Scatter(x=times, y=tr_waterHot,  name='Water Hot T',  line = dict(color = 'dodgerblue',width = 1,dash = 'dot'))
    waterColdTrace= go.Scatter(x=times, y=tr_waterCold, name='Water Cold T', line = dict(color = 'darkturquoise'))
    lossesTrace   = go.Scatter(x=times, y=losses,       name='Losses', yaxis='y2',line = dict(color = 'olive'))
    extractedTrace= go.Scatter(x=times, y=extracted,    name='Extracted', yaxis='y2',line = dict(color = 'black'))

    layout = dict(
        title='Transformer temperatures vs. Time',
        xaxis=dict(
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Losses',
            overlaying ='y',
            side       = 'right',
            range      = [0, 300]
        ),
        height = 500,

        legend=dict(
            x=1,
            y=1
        )
    )
    fig = go.Figure(data=[solidTrace, oilHotTrace, waterHotTrace, waterColdTrace,lossesTrace,extractedTrace], layout=layout)
    iplot(fig)
def cv_adjust(solid_water_trans, solid_int,water_int,waterC,PF,V,wind,temp):
    temperature = temp
    wind        = wind
    [powerFactor,gridVoltage] = [PF, V]

    initialState = machineState(temperature)
    initialState.converter.solid_water_trans = solid_water_trans
    initialState.converter.solid_int = solid_int
    initialState.converter.water_int = water_int
    initialState.converter.waterC = waterC

    initialState.converter.exchCoeffs = [5.35, 5.35, 5.35, 5.35, 5.35]
    initialState.removeTempLimits()

    stateSeries  = [initialState]


    for i in range(300):
        stateSeries.append(stateSeries[-1].machineTimeStep(wind, powerFactor, gridVoltage, temperature))
        stateSeries[-1].converter.waterCold   = temp

    cv_solid     = [item.converter.solid      for item in stateSeries]
    cv_waterHot  = [item.converter.waterHot   for item in stateSeries]
    cv_waterCold = [item.converter.waterCold  for item in stateSeries]
    losses       = [item.converter.losses     for item in stateSeries]
    extracted    = [item.converter.solidWater for item in stateSeries]
    times        = [item.time                 for item in stateSeries]

    solidTrace    = go.Scatter(x=times, y=cv_solid,     name='Solid T',   line = dict(color = 'lime' ,width = 1,dash = 'dot'))
    waterHotTrace = go.Scatter(x=times, y=cv_waterHot,  name='Water Hot T',  line = dict(color = 'dodgerblue',width = 1,dash = 'dot'))
    waterColdTrace= go.Scatter(x=times, y=cv_waterCold, name='Water Cold T', line = dict(color = 'darkturquoise'))
    lossesTrace   = go.Scatter(x=times, y=losses,       name='Losses', yaxis='y2',line = dict(color = 'olive'))
    extractedTrace= go.Scatter(x=times, y=extracted,    name='Extracted', yaxis='y2',line = dict(color = 'black'))

    layout = dict(
        title='Converter temperatures vs. Time',
        xaxis=dict(
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Losses',
            overlaying ='y',
            side       = 'right',
            range      = [0, 300]
        ),
        height = 500,

        legend=dict(
            x=1,
            y=1
        )
    )
    fig = go.Figure(data=[solidTrace, waterHotTrace, waterColdTrace,lossesTrace,extractedTrace], layout=layout)
    iplot(fig)

def gn_adjust(stator_air_trans, stator_water_trans, rotor_air_trans, airIn_water, stator_int, rotor_int,water_int,waterC,airC,PF,V,wind,temp,temp_0, temp_1):
    temperature = temp
    wind        = wind
    [powerFactor,gridVoltage] = [PF, V]

    initialState = machineState(42.1)
    initialState.generator.stator_air_trans = stator_air_trans
    initialState.generator.stator_water_trans = stator_water_trans
    initialState.generator.rotor_air_trans = rotor_air_trans
    initialState.generator.airIn_water = airIn_water
    initialState.generator.stator_int = stator_int
    initialState.generator.rotor_int = rotor_int
    initialState.generator.water_int = water_int
    initialState.generator.waterC = waterC
    initialState.generator.airC = airC
    initialState.generator.rotor = temp_0
    initialState.generator.stator = temp_0
    initialState.generator.waterHot = temp_1
    initialState.generator.waterCold = temp_1


    initialState.generator.exchCoeffs = [7.5, 7.5, 7.5, 7.5, 7.5]
    initialState.removeTempLimits()

    stateSeries  = [initialState]

    for i in range(480):
        stateSeries.append(stateSeries[-1].machineTimeStep(wind, powerFactor, gridVoltage, temperature))
        #stateSeries[-1].generator.waterCold   = 42.3

    gn_stator    = [item.generator.stator for item in stateSeries]
    gn_rotor     = [item.generator.rotor for item in stateSeries]
    gn_waterHot  = [item.generator.waterHot for item in stateSeries]
    gn_waterCold = [item.generator.waterCold for item in stateSeries]
    losses       = [item.generator.losses for item in stateSeries]
    extracted    = [item.generator.heatOut for item in stateSeries]
    times        = [item.time  for item in stateSeries]

    statorTrace    = go.Scatter(x=times, y=gn_stator,     name='Magnets T',   line = dict(color = 'lime' ,width = 1,dash = 'dot'))
    rotorTrace     = go.Scatter(x=times, y=gn_rotor,    name='Windings T',    line = dict(color = 'orangered'))
    waterHotTrace  = go.Scatter(x=times, y=gn_waterHot,  name='Water Hot T',  line = dict(color = 'dodgerblue',width = 1,dash = 'dot'))
    waterColdTrace = go.Scatter(x=times, y=gn_waterCold, name='Water Cold T', line = dict(color = 'darkturquoise'))
    lossesTrace    = go.Scatter(x=times, y=losses,       name='Losses', yaxis='y2',line = dict(color = 'olive'))
    extractedTrace = go.Scatter(x=times, y=extracted,    name='Extracted', yaxis='y2',line = dict(color = 'black'))

    layout = dict(
        title='Transformer temperatures vs. Time',
        xaxis=dict(
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Losses',
            overlaying ='y',
            side       = 'right',
            range      = [0, 300]
        ),
        height = 500,

        legend=dict(
            x=1,
            y=1
        )
    )
    fig = go.Figure(data=[statorTrace, rotorTrace, waterHotTrace, waterColdTrace,lossesTrace,extractedTrace], layout=layout)
    iplot(fig)
def gb_adjust(solid_oil_trans, oil_water_trans, solid_int, oil_int,water_int,oilC,waterC,PF,V,wind,temp):
    temperature = temp
    wind        = wind
    [powerFactor,gridVoltage] = [PF, V]

    initialState = machineState(temperature)
    initialState.gearbox.solid_oil_trans = solid_oil_trans
    initialState.gearbox.oil_water_trans = oil_water_trans
    initialState.gearbox.solid_int = solid_int
    initialState.gearbox.oil_int = oil_int
    initialState.gearbox.water_int = water_int
    initialState.gearbox.oilC = oilC
    initialState.gearbox.waterC = waterC

    initialState.gearbox.exchCoeffs = [7.88, 7.88, 7.88, 7.88, 7.88]
    initialState.removeTempLimits()

    stateSeries  = [initialState]


    for i in range(300):
        stateSeries.append(stateSeries[-1].machineTimeStep(wind, powerFactor, gridVoltage, temperature))
        stateSeries[-1].gearbox.waterCold   = temp

    gb_solid     = [item.gearbox.solid     for item in stateSeries]
    gb_oilHot    = [item.gearbox.oilHot    for item in stateSeries]
    gb_waterHot  = [item.gearbox.waterHot  for item in stateSeries]
    gb_waterCold = [item.gearbox.waterCold for item in stateSeries]
    losses       = [item.gearbox.losses    for item in stateSeries]
    extracted    = [item.gearbox.oilWater  for item in stateSeries]
    times        = [item.time              for item in stateSeries]

    solidTrace    = go.Scatter(x=times, y=gb_solid,     name='Windings T',   line = dict(color = 'lime' ,width = 1,dash = 'dot'))
    oilHotTrace   = go.Scatter(x=times, y=gb_oilHot,    name='Oil Hot T',    line = dict(color = 'orangered'))
    waterHotTrace = go.Scatter(x=times, y=gb_waterHot,  name='Water Hot T',  line = dict(color = 'dodgerblue',width = 1,dash = 'dot'))
    waterColdTrace= go.Scatter(x=times, y=gb_waterCold, name='Water Cold T', line = dict(color = 'darkturquoise'))
    lossesTrace   = go.Scatter(x=times, y=losses,       name='Losses', yaxis='y2',line = dict(color = 'olive'))
    extractedTrace= go.Scatter(x=times, y=extracted,    name='Extracted', yaxis='y2',line = dict(color = 'black'))

    layout = dict(
        title='Gearbox temperatures vs. Time',
        xaxis=dict(
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Losses',
            overlaying ='y',
            side       = 'right',
            range      = [0, 300]
        ),
        height = 500,

        legend=dict(
            x=1,
            y=1
        )
    )
    fig = go.Figure(data=[solidTrace, oilHotTrace, waterHotTrace, waterColdTrace,lossesTrace,extractedTrace], layout=layout)
    iplot(fig)
