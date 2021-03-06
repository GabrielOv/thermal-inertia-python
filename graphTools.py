
import plotly.plotly as py
import plotly.offline as pyoff
import plotly.graph_objs as go
import numpy as np
from plotly import tools
from datetime import datetime

import config

# Graphs related with component internal temperatures and ambient conditions
def outputRequestedGraphs(stateSeries):
    windPowerGraphs(stateSeries)
    windTemperatureHeatMap(stateSeries)
    lossesGraph(stateSeries)

    graphTransformer(stateSeries)
    graphConverter(stateSeries)
    graphGenerator(stateSeries)
    graphGearbox(stateSeries)
    graphNacelle(stateSeries)
    graphTower(stateSeries)

# Timeseries of wind and potential production given a certain power curve
def windPowerGraphs(stateSeries):

    powers = [item.potential for item in stateSeries[0::config.reductionFactor]]
    winds  = [item.wind      for item in stateSeries[0::config.reductionFactor]]
    times  = [item.time      for item in stateSeries[0::config.reductionFactor]]
    traceWind  = go.Scatter(x=times, y=winds,  name='Wind Speed')
    tracePower = go.Scatter(x=times, y=powers, name='Produced Power', yaxis='y2')

    layout = dict(
        title='Wind Data Series in Bremerhaven Airport',
        xaxis=dict(
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Wind Speed [m/s]'
        ),
        yaxis2=dict(
            title='Produced Power [MW]',
            overlaying='y',
            side='right'
        )
    )
    data = [tracePower, traceWind]
    fig = go.Figure(data=data, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'windSeries.html'), auto_open=False )
# Probability distribution for wind temperature, and the combination of boht as a heatmap
def windTemperatureHeatMap(stateSeries):
    temperatures = [item.Tamb    for item in stateSeries]
    winds        = [item.wind    for item in stateSeries]

    trace_WT     = go.Scatter(x = temperatures[0::100],
                              y = winds[0::100],
                              name = 'points',
                              mode = 'markers',
                              marker = dict(color = 'black', size = 2, opacity = 0.1))
    trace_hist2D = go.Histogram2dcontour(x = temperatures,
                                         y = winds,
                                         name         = 'density',
                                         ncontours    = 20,
                                         colorscale   = 'Blues',
                                         reversescale = True,
                                         showscale    = False,
                                         histnorm     = 'probability')
    trace_histT  = go.Histogram(x = temperatures,
                                name     = 'temperatures density',
                                marker   = dict(color='powderblue'),
                                histnorm = 'probability',
                                yaxis    = 'y2',
                                autobinx = False,
                                xbins    = dict(start = -15, end = 35, size = 0.5))
    trace_histW  = go.Histogram(y = winds,
                                name     ='winds density',
                                marker   = dict(color='powderblue'),
                                histnorm = 'probability',
                                xaxis    = 'x2',
                                autobiny = False,
                                ybins    = dict(start = 0, end = 30, size = 0.5))

    trafoAlarms = [item    for item in stateSeries if item.transformer.alarm]
    convAlarms  = [item    for item in stateSeries if item.converter.alarm]
    generAlarms = [item    for item in stateSeries if item.generator.alarm]
    gearbAlarms = [item    for item in stateSeries if item.gearbox.alarm]

    trafoExcesWTScatter = go.Scatter(x = [item.Tamb    for item in trafoAlarms],
                                     y = [item.wind    for item in trafoAlarms],
                                     mode   = 'markers',
                                     name   = 'Trafo Alarms',
                                     marker = dict(color = 'red', size = 5, opacity = 0.4))
    convExcesWTScatter  = go.Scatter(x = [item.Tamb    for item in convAlarms],
                                     y = [item.wind    for item in convAlarms],
                                     mode   = 'markers',
                                     name   = 'Converter Alarms',
                                     marker = dict(color = 'aqua', size = 4, opacity = 0.4))
    generExcesWTScatter = go.Scatter(x = [item.Tamb    for item in generAlarms],
                                     y = [item.wind    for item in generAlarms],
                                     mode   = 'markers',
                                     name   = 'Generator Alarms',
                                     marker = dict(color = 'lime', size = 3, opacity = 0.4))
    gearbExcesWTScatter = go.Scatter(x = [item.Tamb    for item in gearbAlarms],
                                     y = [item.wind    for item in gearbAlarms],
                                     mode   = 'markers',
                                     name   = 'Gearbox Alarms',
                                     marker = dict(color = 'magenta', size = 4, opacity = 0.4))

    data = [trace_hist2D, trace_histT, trace_histW,
            trafoExcesWTScatter,
            convExcesWTScatter,
            generExcesWTScatter,
            gearbExcesWTScatter]

    layout = go.Layout(
        showlegend=False,
        xaxis=dict(
            domain=[0, 0.85],
            showgrid=False,
            zeroline=False,
            title='Temperature [C deg]'
        ),
        yaxis=dict(
            domain=[0, 0.85],
            showgrid=False,
            zeroline=False,
            title='Wind Speed [m/s]'
        ),
        margin=dict(
            t=50
        ),
        hovermode='closest',
        bargap=10,
        xaxis2=dict(
            domain=[0.9, 1],
            showgrid=False,
            zeroline=False
        ),
        yaxis2=dict(
            domain=[0.9, 1],
            showgrid=False,
            zeroline=False
        )
    )

    fig = go.Figure(data=data, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'temp-wind-heatmap.html'), auto_open=False)
# Timeseries of heat losses generated by each component
def lossesGraph(stateSeries):
    time = [item.time for item in stateSeries[0::config.reductionFactor]]
    traceTrafo = go.Scatter(x=time,  y=[item.transformer.losses for item in stateSeries[0::config.reductionFactor]],  name='Transformer losses')
    traceConv  = go.Scatter(x=time,  y=[item.converter.losses   for item in stateSeries[0::config.reductionFactor]],  name='Converter losses')
    traceGener = go.Scatter(x=time,  y=[item.generator.losses   for item in stateSeries[0::config.reductionFactor]],  name='Generator losses')
    traceGearb = go.Scatter(x=time,  y=[item.gearbox.losses     for item in stateSeries[0::config.reductionFactor]],  name='Gearbox losses')

    layout = dict(
        title='Heat losses per component vs. Time',
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(count=6,
                         label='6m',
                         step='month',
                         stepmode='backward'),
                    dict(count=1,
                        label='YTD',
                        step='year',
                        stepmode='todate'),
                    dict(count=1,
                        label='1y',
                        step='year',
                        stepmode='backward'),
                    dict(step='all')
                ])
            ),
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Wind Speed [m/s]'
        )
    )
    data = [traceTrafo, traceConv, traceGener, traceGearb]
    fig = go.Figure(data=data, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'lossesGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the TRANSFORMER
def graphTransformer(stateSeries):

    trafoReducedSeries = reduceTrafoPoints(stateSeries)

    trafoGraph        = [[item.transformer.solid    for item in trafoReducedSeries],
                        [item.transformer.oilHot    for item in trafoReducedSeries],
                        [item.transformer.oilCold   for item in trafoReducedSeries],
                        [item.transformer.waterHot  for item in trafoReducedSeries],
                        [item.transformer.waterCold for item in trafoReducedSeries],
                        [item.transformer.exchMode  for item in trafoReducedSeries],
                        [item.Tamb                  for item in trafoReducedSeries],
                        [item.transformer.oilHot    for item in stateSeries if item.transformer.alarm]]
    trafoReducedTimes = [item.time for item in trafoReducedSeries]
    trafoExcesTimes   = [item.time for item in stateSeries if item.transformer.alarm]

    traceTrafo=[]
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[0],
                                 name = 'Windings T',
                                 line = dict(color = 'lime', width = 1, dash = 'dot')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[1],
                                 name = 'Oil Hot T',
                                 line = dict(color = 'orangered')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[2],
                                 name = 'Oil Cold T',
                                 line = dict(color = 'tomato', width = 1, dash = 'dot')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[3],
                                 name = 'Water Hot T',
                                 line = dict(color = 'dodgerblue',width = 1,dash = 'dot')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[4],
                                 name = 'Water Cold T',
                                 line = dict(color = 'darkturquoise')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[5],
                                 name  = 'Exchanger mode',
                                 yaxis = 'y2',
                                 line  = dict(color = 'olive')))
    traceTrafo.append(go.Scatter(x = trafoReducedTimes,
                                 y = trafoGraph[6],
                                 name = 'Ambient T',
                                 line = dict(color = 'black')))
    traceTrafo.append(go.Scatter(x = trafoExcesTimes,
                                 y = trafoGraph[7],
                                 name = 'Temperature ALARM!!',
                                 mode = 'markers',
                                 marker = dict(size = 10, color = 'red')))


    layout = dict(
        title='Transformer temperatures vs. Time',
        xaxis=dict(
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Exchanger mode [-]',
            overlaying ='y',
            side       = 'right',
            range      = [0, 20]
        )
    )

    fig = go.Figure(data=traceTrafo, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'trafoTempsGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the CONVERTER
def graphConverter(stateSeries):
    converterReducedSeries= reduceConverterPoints(stateSeries)

    convGraph = [[item.converter.solid     for item in converterReducedSeries],
                 [item.converter.waterHot  for item in converterReducedSeries],
                 [item.converter.waterCold for item in converterReducedSeries],
                 [item.converter.exchMode  for item in converterReducedSeries],
                 [item.Tamb                for item in converterReducedSeries],
                 [item.converter.waterCold for item in stateSeries if item.converter.alarm]]
    converterReducedTimes = [item.time for item in converterReducedSeries]
    converterExcesTimes   = [item.time for item in stateSeries if item.converter.alarm]

    traceConv = []
    traceConv.append(go.Scatter(x = converterReducedTimes,
                                y = convGraph[0],
                                name = 'Solid T',
                                line = dict(color = 'lime', width = 1, dash = 'dot')))
    traceConv.append(go.Scatter(x = converterReducedTimes,
                                y = convGraph[1],
                                name = 'Water Hot T',
                                line = dict(color = 'dodgerblue', width = 1, dash = 'dot')))
    traceConv.append(go.Scatter(x = converterReducedTimes,
                                y = convGraph[2],
                                name = 'Water Cold T',
                                line = dict(color = 'darkturquoise')))
    traceConv.append(go.Scatter(x = converterReducedTimes,
                                y = convGraph[3],
                                name  = 'Exchanger mode',
                                yaxis = 'y2',
                                line  = dict(color = 'olive')))
    traceConv.append(go.Scatter(x = converterReducedTimes,
                                y = convGraph[4],
                                name = 'Ambient T',
                                line = dict(color = 'black')))
    traceConv.append(go.Scatter(x = converterExcesTimes,
                                y = convGraph[5],
                                name = 'Temperature ALARM!!',
                                mode = 'markers',
                                marker = dict(size = 10, color = 'red',)))


    layout = dict(
        title='Converter temperatures vs. Time',
        xaxis=dict(
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Exchanger mode [-]',
            overlaying ='y',
            side       = 'right',
            range      = [0, 20]
        )
    )

    fig = go.Figure(data=traceConv, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'converterTempsGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the GENERATOR
def graphGenerator(stateSeries):

    generatorReducedSeries = reduceGeneratorPoints(stateSeries)

    generatorGraph=[[item.generator.stator    for item in generatorReducedSeries],
                    [item.generator.rotor     for item in generatorReducedSeries],
                    [item.generator.airHot    for item in generatorReducedSeries],
                    [item.generator.airCold   for item in generatorReducedSeries],
                    [item.generator.waterHot  for item in generatorReducedSeries],
                    [item.generator.waterCold for item in generatorReducedSeries],
                    [item.generator.exchMode  for item in generatorReducedSeries],
                    [item.Tamb                for item in generatorReducedSeries],
                    [item.generator.waterCold for item in stateSeries if item.generator.alarm]]
    generatorReducedTimes = [item.time for item in generatorReducedSeries]
    generatorExcesTimes   = [item.time for item in stateSeries if item.generator.alarm]

    traceGenerator = []
    traceGenerator.append(go.Scatter(x=generatorReducedTimes,
                                     y=generatorGraph[0],
                                     name='Stator T',
                                     line = dict(color = 'lime', width = 1, dash = 'dot')))
    traceGenerator.append(go.Scatter(x=generatorReducedTimes,
                                     y=generatorGraph[1],
                                     name='Rotor T',
                                     line = dict(color = 'springgreen', width = 1, dash = 'dot')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[2],
                                     name = 'Air Hot T',
                                     line = dict(color = 'tan', width = 1, dash = 'dot')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[3],
                                     name = 'Air Cold T',
                                     line = dict(color = 'navajowhite', width = 1, dash = 'dot')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[4],
                                     name = 'Water Hot T',
                                     line = dict(color = 'dodgerblue', width = 1, dash = 'dot')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[5],
                                     name = 'Water Cold T',
                                     line = dict(color = 'darkturquoise')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[6],
                                     name  = 'Exchanger mode',
                                     yaxis = 'y2',
                                     line  = dict(color = 'olive')))
    traceGenerator.append(go.Scatter(x = generatorReducedTimes,
                                     y = generatorGraph[7],
                                     name = 'Ambient T',
                                     line = dict(color = 'black')))
    traceGenerator.append(go.Scatter(x = generatorExcesTimes,
                                     y = generatorGraph[8],
                                     name = 'Temperature ALARM!!',
                                     mode = 'markers',
                                     marker = dict(size = 10, color = 'red')))

    layout = dict(
        title='Generator temperatures vs. Time',
        xaxis=dict(
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Exchanger mode [-]',
            overlaying ='y',
            side       = 'right',
            range      = [0, 20]
        )
    )

    fig = go.Figure(data=traceGenerator, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'generatorTempsGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the GEARBOX
def graphGearbox(stateSeries):

    gearboxReducedSeries = reduceGearboxPoints(stateSeries)

    gearboxGraph=[[item.gearbox.solid     for item in gearboxReducedSeries],
                  [item.gearbox.oilHot    for item in gearboxReducedSeries],
                  [item.gearbox.oilCold   for item in gearboxReducedSeries],
                  [item.gearbox.waterHot  for item in gearboxReducedSeries],
                  [item.gearbox.waterCold for item in gearboxReducedSeries],
                  [item.gearbox.exchMode  for item in gearboxReducedSeries],
                  [item.Tamb              for item in gearboxReducedSeries],
                  [item.gearbox.oilCold   for item in stateSeries if item.gearbox.alarm]]
    gearboxReducedTimes = [item.time for item in gearboxReducedSeries]
    gearboxExcesTimes   = [item.time for item in stateSeries if item.gearbox.alarm]

    traceGear = []
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[0],
                                name = 'Solid T',
                                line = dict(color = 'lime', width = 1, dash = 'dot')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[1],
                                name = 'Oil Hot T',
                                line = dict(color = 'orangered', width = 1, dash = 'dot')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[2],
                                name = 'Oil Cold T',
                                line = dict(color = 'tomato')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[3],
                                name = 'Water Hot T',
                                line = dict(color = 'dodgerblue',width = 1, dash = 'dot')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[4],
                                name = 'Water Cold T',
                                line = dict(color = 'darkturquoise')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[5],
                                name  = 'Exchanger mode',
                                yaxis = 'y2',
                                line  = dict(color = 'olive')))
    traceGear.append(go.Scatter(x = gearboxReducedTimes,
                                y = gearboxGraph[6],
                                name = 'Ambient T',
                                line = dict(color = 'black')))
    traceGear.append(go.Scatter(x = gearboxExcesTimes,
                                y = gearboxGraph[7],
                                name   = 'Temperature ALARM!!',
                                mode   = 'markers',
                                marker = dict(size = 10, color = 'red',)))

    layout = dict(
        title='Gearbox temperatures vs. Time',
        xaxis=dict(
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        ),
        yaxis2=dict(
            title      ='Exchanger mode [-]',
            overlaying ='y',
            side       = 'right',
            range      = [0, 20]
        )
    )

    fig = go.Figure(data=traceGear, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'gearTempsGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the NACELLE
def graphNacelle(stateSeries):

    nacelleReducedSeries = reduceNacellePoints(stateSeries)

    nacGraph = [[item.air_component.temperature['Nacelle_top_rear']     for item in nacelleReducedSeries],
                [item.air_component.temperature['Nacelle_top_front']    for item in nacelleReducedSeries],
                [item.air_component.temperature['Nacelle_bottom_rear']  for item in nacelleReducedSeries],
                [item.air_component.temperature['Nacelle_bottom_front']  for item in nacelleReducedSeries],
                [(item.air_component.heatFlows[('Nacelle_bottom_rear','Nacelle_top_rear')]
                 + item.air_component.heatFlows[('Nacelle_top_front','Nacelle_top_rear')]
                 + item.air_component.heatFlows[('Nacelle_bottom_rear','Nacelle_bottom_front')]
                 + item.air_component.heatFlows[('Nacelle_bottom_front','Nacelle_top_front')])/1000  for item in nacelleReducedSeries],
                [-item.air_component.heatFlows[('Nacelle_top_rear','Nacelle_bottom_rear')]/1000  for item in nacelleReducedSeries],
                [item.Tamb                  for item in nacelleReducedSeries],
                [item.air_component.temperature['Hub']  for item in nacelleReducedSeries]]
    nacelleTimes = [item.time for item in nacelleReducedSeries]
    # nacelleExcesTimes   = [item.time for item in stateSeries if item.nacelle.alarm]

    traceNac = []
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[0],
                               name = 'Exch Out T',
                               line = dict(color = 'lime', width = 1)))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[1],
                               name = 'Exch Intake T',
                               line = dict(color = 'seagreen', width = 1)))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[2],
                               name = 'Nacelle Bottom T',
                               line = dict(color = 'dodgerblue', width = 1)))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[3],
                               name = 'Nacelle Top Front W',
                            #    yaxis = 'y2',
                               line = dict(color = 'darkturquoise')))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[4],
                               name  = 'Components In W',
                            #    yaxis = 'y2',
                               line  = dict(color = 'olive')))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[5],
                               name  = 'Exchanger Out In W',
                            #    yaxis = 'y2',
                               line  = dict(color = 'green')))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[6],
                               name = 'Ambient T',
                               line = dict(color = 'black')))
    traceNac.append(go.Scatter(x = nacelleTimes,
                               y = nacGraph[6],
                               name = 'Hub T',
                               line = dict(color = 'orange')))


    layout = dict(
        title='Nacelle temperatures vs. Time',
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(count=6,
                         label='6m',
                         step='month',
                         stepmode='backward'),
                    dict(count=1,
                        label='YTD',
                        step='year',
                        stepmode='todate'),
                    dict(count=1,
                        label='1y',
                        step='year',
                        stepmode='backward'),
                    dict(step='all')
                ])
            ),
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        # ),
        # yaxis2=dict(
        #     title      ='Exchanger mode [-]',
        #     overlaying ='y',
        #     side       = 'right',
        #     range      = [0, 100]
        )
    )

    fig = go.Figure(data=traceNac, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'nacelleTempsGraph.html'), auto_open=False)
# Timeseries of temperate and cooling conditions in the TOWER
def graphTower(stateSeries):

    towerReducedSeries = reduceTowerPoints(stateSeries)

    towGraph = [[item.air_component.temperature['Tower_top']            for item in towerReducedSeries],
                [item.air_component.temperature['Converter_platform']   for item in towerReducedSeries],
                [item.air_component.temperature['Transformer_platform'] for item in towerReducedSeries],
                [item.air_component.temperature['Switchgear_platform']  for item in towerReducedSeries],
                [item.air_component.temperature['Tower_middle']         for item in towerReducedSeries],
                [(item.air_component.heatFlows[('Switchgear_inlet','Switchgear_platform')]
                 + item.air_component.heatFlows[('Transformer_inlet','Transformer_platform')]
                 + item.air_component.heatFlows[('Converter_inlet','Converter_platform')])/1000  for item in towerReducedSeries],
                [-(item.air_component.heatFlows[('Switchgear_platform','Transformer_platform')]
                 + item.air_component.heatFlows[('Transformer_platform','Converter_platform')]
                 + item.air_component.heatFlows[('Converter_platform', 'Tower_middle')]
                 + item.air_component.heatFlows[('Tower_middle','Tower_top')])/1000  for item in towerReducedSeries],
                [item.Tamb                  for item in towerReducedSeries]]
    towerTimes = [item.time for item in towerReducedSeries]
    # nacelleExcesTimes   = [item.time for item in stateSeries if item.nacelle.alarm]

    traceTow = []
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[0],
                               name = 'Tower top T',
                               line = dict(color = 'lime', width = 1)))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[1],
                               name = 'Converter plat T',
                               line = dict(color = 'seagreen', width = 1)))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[2],
                               name = 'Transformer plat T',
                               line = dict(color = 'dodgerblue', width = 1)))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[3],
                               name = 'Switchgear plat W',
                            #    yaxis = 'y2',
                               line = dict(color = 'darkturquoise')))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[4],
                               name  = 'Tower Middle T',
                            #    yaxis = 'y2',
                               line  = dict(color = 'olive')))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[5],
                               name  = 'Tower components W',
                            #    yaxis = 'y2',
                               line  = dict(color = 'green')))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[6],
                               name  = 'Tower cooling W',
                            #    yaxis = 'y2',
                               line  = dict(color = 'orange')))
    traceTow.append(go.Scatter(x = towerTimes,
                               y = towGraph[7],
                               name = 'Ambient T',
                               line = dict(color = 'black')))
    # traceTow.append(go.Scatter(x = nacelleExcesTimes,
    #                            y = nacGraph[7],
    #                            name = 'Temperature ALARM!!',
    #                            mode = 'markers',
    #                            marker = dict(size = 10, color = 'red',)))


    layout = dict(
        title='Nacelle temperatures vs. Time',
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(count=6,
                         label='6m',
                         step='month',
                         stepmode='backward'),
                    dict(count=1,
                        label='YTD',
                        step='year',
                        stepmode='todate'),
                    dict(count=1,
                        label='1y',
                        step='year',
                        stepmode='backward'),
                    dict(step='all')
                ])
            ),
            rangeslider=dict(),
            type='date'
        ),
        yaxis=dict(
            title='Temperature [deg C]'
        # ),
        # yaxis2=dict(
        #     title      ='Exchanger mode [-]',
        #     overlaying ='y',
        #     side       = 'right',
        #     range      = [0, 100]
        )
    )

    fig = go.Figure(data=traceTow, layout=layout)
    pyoff.plot(fig, filename= (config.currentLocation+'towerTempsGraph.html'), auto_open=False)
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on transformer.oilHot
def reduceTrafoPoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].transformer.oilHot > outputSeries[-1].transformer.oilHot):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on converter.waterCold
def reduceConverterPoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].converter.waterCold > outputSeries[-1].converter.waterCold):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on generator.waterCold
def reduceGeneratorPoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].generator.waterCold > outputSeries[-1].generator.waterCold):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on gearbox.oilCold
def reduceGearboxPoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].gearbox.oilCold > outputSeries[-1].gearbox.oilCold):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on Nacelle_top_rear
def reduceNacellePoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].air_component.temperature['Nacelle_top_rear'] > outputSeries[-1].air_component.temperature['Nacelle_top_rear']):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Reduces the timeseries to get more manageable graphs, takes the most adverse of every 10 points based on Converter_platform
def reduceTowerPoints(inputSeries):
    outputSeries = []
    for i in range(len(inputSeries)-1):
        if (i%config.reductionFactor == 0):
            outputSeries.append(inputSeries[i])
        if (i%config.reductionFactor != 0) & (inputSeries[i].air_component.temperature['Converter_platform'] > outputSeries[-1].air_component.temperature['Converter_platform']):
            outputSeries[-1] = inputSeries[i]
    return outputSeries
# Timeseries comparing achievable power production and desired grid conditions with those necessary due to derating
def powerVsPotentialgraph(stateSeries):
        potentialPower  = [item.potential/1000  for item in stateSeries]
        times           = [item.time  for item in stateSeries]
        deratedPower    = [item.power/1000 for item in stateSeries]
        deratedPF       = [item.PF    for item in stateSeries]
        deratedV        = [item.V     for item in stateSeries]

        tracePowerPot = go.Scatter(x=times[0::config.reductionFactor],  y=potentialPower[0::config.reductionFactor],  name='Potential Power',line = dict(color = 'blue', width = 1,dash = 'dot'))
        tracePower    = go.Scatter(x=times[0::config.reductionFactor],  y=deratedPower[0::config.reductionFactor],  name='Derated Power')

        tracePF = go.Scatter(x=times[0::config.reductionFactor], y=deratedPF[0::config.reductionFactor], name='Power Factor', yaxis='y2')
        traceV  = go.Scatter(x=times[0::config.reductionFactor], y=deratedV[0::config.reductionFactor], name='Grid Voltage', yaxis='y2')

        layout = dict(
            title='Power Series in Bremerhaven Airport',
            xaxis=dict(
                rangeslider=dict(),
                type='date'
            ),
            yaxis=dict(
                title='Produced Power [MW]'
            ),
            yaxis2=dict(
                title='Power Factor and V Grid [-]',
                overlaying='y',
                side='right',
                range      = [0, 1.1]
            )
        )
        data = [tracePowerPot, tracePower, tracePF, traceV]
        fig = go.Figure(data=data, layout=layout)
        pyoff.plot(fig, filename= (config.currentLocation+'potentialPowerSeries.html'), auto_open=False)
