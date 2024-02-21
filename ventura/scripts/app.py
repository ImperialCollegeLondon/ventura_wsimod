
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import time
import ast
#import sys
import os
import pandas as pd
from ventura.scripts import manchester_sim_wrapper_ED_ver1oct22 as msw
from ventura.scripts import manchester_sim_wrapper_ED_verNov as mswNov
from pathlib import Path
# from Fenfield_demoVK import SimEnfield6catchments as EnfSim


#from RunManchesterSimWrapper_ED_Ver1oct22 import simulateAPIcall #should be made redundant
app = Flask(__name__)
cors = CORS(app)


app.config["DEBUG"] = True
#APIurl='https://bingfield.drawscapes.com/vdr_send'#now redundant??
#FormURL='TryForm4input.html'
FormURL='vdr.html'
DefaultDays2delete=100#the dafault 'run-in' period
DefaultVdrSimLength=2#for BGS VDR as in 2023
#Ncalls=0#was trying a work around - currently not needed

dates = pd.date_range('2012-07-30','2012-07-31',freq='D')#this is a subset for what is currently available
#dates = pd.date_range('2002-07-30','2002-07-31',freq='D')#I think that was for the storm event?
ManRiverFlows_=[]
x=[]#[]#3#x is for the lags (number of days); was [] in crane_sim_wrapper
#table2display=[]
##### initialises model information#######

data_dir = os.path.join(
    os.path.dirname(
            os.path.dirname(
                    os.path.abspath(__file__))),
    "data", "manchester")
#NB: these dates are just to initialise the model, the real run will be defined later
#nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = msw.load_manchester(data_dir,dates)#NB calling msw should be ok even
#if the the Nov version (i.e. mswNov) is used later on with e.g. vdr_sendDict2 or vdr_send2 http end points
nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = mswNov.load_manchester(data_dir,dates)#


list_of_nodes = nodes.loc[nodes['type'] == 'catchment'].index
df = pd.DataFrame(list_of_nodes)
list_of_nodes = df.values.tolist()

###########
###########Below is the new bit - for Enfield
# @app.route('/vdr_SendDictEnfield', methods=["GET", "POST"])
# #this will receive the data, run Fenfield_demoVK, and return the results
# def GetDictToFenfieldDemoReturnWSIMODenfield():
#     # brings json data and returns it.
#     data1 = request
#     data=ast.literal_eval(data1.json)# to reinstate the dictionary
#     NewBuiltUpEnf=data['NewBuiltUp']
#     NewPopulationEnf=data['NewPopulation']
#     StartDateEnf=data['StartDate']
#     EndDateEnf=data['EndDate']
#     PopulationGrowthEnf=data['PopulationGrowthEnf']
#     RainfallMultiplierEnf=data['RainfallMultiplierEnf']
#     EnfArcs,EnfNodes,EnfFlows, EnfTanks, pymmes_flow,salmon_flow,turkey_flow, qdf,qdf_S,qdf_T, ModifiedEnf_land_node_info=\
#                 EnfSim(NewBuiltUp=NewBuiltUpEnf,NewPopulation=NewPopulationEnf,StartDate=StartDateEnf,EndDate=EndDateEnf,\
#                 RainfallMultiplier=RainfallMultiplierEnf, PopulationGrowth=PopulationGrowthEnf)
#     EnfRiverArcs=['pymmes-river','pymmes-urban-waste','salmon-river','salmon-urban-waste','turkey-river','turkey-urban-waste']
#     EnfFlows_= EnfFlows.pivot(index='time', columns='arc',values='flow')
#     EnfTanks_= EnfTanks.pivot(index='time', columns='node',values='storage')

#     EnfRiverFlows=pd.DataFrame()
#     for item in EnfRiverArcs:
#         EnfRiverFlows[item]=EnfFlows_[item]


#     #now for the storm flows:
#     EnfStormdischargeFlows=pd.DataFrame()
#     for item in ModifiedEnf_land_node_info.index:
#         item_=item+'-storm-to-outlet'
#         EnfStormdischargeFlows[item_]=EnfFlows_[item_]

#     #Now will deal with WQ
#     EnfPhosphate=EnfFlows.pivot(index='time', columns='arc',values='phosphate')
#     EnfRiverP=pd.DataFrame()
#     for item in EnfRiverArcs:
#         EnfRiverP[item]=EnfPhosphate[item]


#     EnfNitrate= EnfFlows.pivot(index='time', columns='arc',values='nitrate')
#     EnfRiverNitrate=pd.DataFrame()
#     for item in EnfRiverArcs:
#         EnfRiverNitrate[item]=EnfNitrate[item]

#     EnfAmmonia= EnfFlows.pivot(index='time', columns='arc',values='ammonia')
#     EnfRiverAmmonia=pd.DataFrame()
#     for item in EnfRiverArcs:
#         EnfRiverAmmonia[item]=EnfAmmonia[item]

#     EnfRiverDFcolumns=EnfRiverFlows.columns.to_list()
#     RequestedSimDates = pd.date_range(StartDateEnf,EndDateEnf,freq='D')#this is a subset for what is currently available

#     #################
#     #below is the bit added in Jun 2023 to cut the initial 'run-in' period

#     try:
#         days2delete=data['days2delete']#
#         MinSimLength=data['MinSimLength']#

#     except:
#         days2delete=DefaultDays2delete#to improve
#         MinSimLength=DefaultVdrSimLength


#     if (len(RequestedSimDates)-MinSimLength)<=days2delete:
#         start=max(0,len(RequestedSimDates)-MinSimLength)
#     else:
#         start=days2delete


#     return jsonify(EnfRiverDFcolumns=EnfRiverFlows.columns.to_list(),\
#         EnfRiverFlows=EnfRiverFlows[start:].values.tolist(),EnfTanks=EnfTanks.loc[EnfTanks['time']>=RequestedSimDates[start]].values.tolist(),\
#         EnfStormdischargeFlows=EnfStormdischargeFlows[start:].values.tolist(),EnfRiverP=EnfRiverP[start:].values.tolist(),\
#         EnfRiverNitrate=EnfRiverNitrate[start:].values.tolist(),EnfRiverAmmonia=EnfRiverAmmonia[start:].values.tolist(),\
#         SimulationDates=RequestedSimDates[start:].values.tolist())# did not work: ModifiedEnf_land_node_info=ModifiedEnf_land_node_info
from datetime import datetime


##########Below is for Manchester#############
#this version will accept an enchanced list of inputs and return more results
@app.route('/vdr_SendDict2', methods=["GET", "POST"])
#this will receive the data, run WSIMOD, and return the results
def GetDictToAPIreturnWSIMODenhanced():
    # brings json data and returns it.
    data = request.json
    if not isinstance(data,dict):
        data=ast.literal_eval(data)#trying to reinstate the dictionary

    # Generate a timestamp for the file name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"ui_call_{timestamp}.json"

    # File path to save the JSON data
    file_dir = Path().cwd().parent / 'data' / 'ui_calls'
    file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / file_name

    # Dump the dictionary to a JSON file
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file)

    # This will create a file with a name like "output_20231206124530.json" (year, month, day, hour, minute, second)
    nodes_numbers_to_change=data['nodes_numbers_to_change']
    RC_to_change=data['RC_to_change']
    catchmentN4populationChange=data['catchmentN4populationChange']
    PopulationChange=data['PopulationChange']
    StartDate=data['StartDate']
    EndDate=data['EndDate']
    catchmentN4wiltPointChange=data['catchmentN4wiltPointChange']
    newWiltPointMultiplier=data['newWiltPointMultiplier']
    catchmentN4demandChange=data['catchmentN4demandChange']
    NewPerCapitaDemand=data['NewPerCapitaDemand']
    PopulationGrowth=data['PopulationGrowth']
    RainfallMultiplier=data['RainfallMultiplier']

    RequestedSimDates = pd.date_range(StartDate,EndDate,freq='D')#this is a subset for what is currently available


    #develops a list of nodes to change for RC
    node_names_to_change = []
    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
        print('RC will change in: ', list_of_nodes[i][0])

    #develops a list of nodes for population change
    NodeNames4populationChange = []
    for ii in catchmentN4populationChange:
        NodeNames4populationChange.append(list_of_nodes[ii][0])
        print('and the population will change in: ', list_of_nodes[ii][0])
    NodeNames4wiltPointChange=GetListOfNodeNamesFromTheirNumbers(catchmentN4wiltPointChange, list_of_nodes)
    NodeNames4demandChange=GetListOfNodeNamesFromTheirNumbers(catchmentN4demandChange, list_of_nodes)


    #historically, list_results is same as ManRiverFlows
    ManFlowsDemand2foul, ManRiverNitrate, ManRiverAmmonia, ManRiverP,tanks, list_results, ManWWTPdischargeFlows,\
        ManSewerFlows, ManStormdischargeFlows,ManFoulToStormFlows, ManLandToOutletFlows, ManExcessWater=\
        callWSIMODfromFlaskEnhanced(node_names_to_change, RC_to_change,
        NodeNames4populationChange,PopulationChange,
        RequestedSimDates,RainfallMultiplier,
        NodeNames4wiltPointChange, newWiltPointMultiplier,
        NodeNames4demandChange, NewPerCapitaDemand, PopulationGrowth)

    # list_results.to_csv(file_path.replace('.json','_flows.csv'), index=False)
    ManRiverDFcolumns=list_results.columns.to_list()
    #BD edit 2023-09-18
    #ManSewerDFcolumns=ManSewerFlows.columns.to_list()
    ManSewerDFcolumns = ManRiverDFcolumns
    #end edit
    ManWWTPdischargeDFcolumns=ManWWTPdischargeFlows.columns.to_list()

    #below is the bit added in Apr 2023 to cut the initial 'run-in' period
    try:
        days2delete=data['days2delete']#
        MinSimLength=data['MinSimLength']#

    except:
        days2delete=DefaultDays2delete#to improve
        MinSimLength=DefaultVdrSimLength

    #DfsNames=['ManFlowsDemand2foul', 'ManRiverNitrate', 'ManRiverAmmonia', 'ManRiverP','tanks', 'list_results','ManWWTPdischargeFlows','ManSewerFlows','RequestedSimDates', 'ManStormdischargeFlows','ManFoulToStormFlows']

    if (len(RequestedSimDates)-MinSimLength)<=days2delete:
        start=max(0,len(RequestedSimDates)-MinSimLength)
    else:
        start=days2delete
    '''
    #try:
    for item in DfsNames:
        str2exec=item + '=' + item + '[' +str(start) +':]'
        exec(str2exec)
        str2exec='ManFlowsDemand2foul=ManFlowsDemand2foul[5:]'#for debug only
        exec(str2exec)
    '''

    #ManFlowsDemand2foul=ManFlowsDemand2foul[start:]#for debug only
    '''
    except Exception as e:
        str2display='Something is not quite right;'
        str2display+=' and the error was ' + str(e)
        str2display+=' whilst str2exec was ' + str2exec
        return jsonify(str2display)
    '''
    '''
    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul_.values.tolist(), ManRiverNitrate=ManRiverNitrate_.values.tolist(),
        ManRiverAmmonia=ManRiverAmmonia_.values.tolist(),ManRiverP=ManRiverP_.values.tolist(), tanks=tanks_.values.tolist(),
        ManRiverFlows = list_results_.values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows_.values.tolist(),
        ManSewerFlows = ManSewerFlows_.values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates_.to_list(),
        ManStormdischargeFlows=ManStormdischargeFlows_.values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
        ManFoulToStormFlows=ManFoulToStormFlows_.values.tolist())
    '''
    #tanks=tanks.loc[tanks['time']>=RequestedSimDates[start]].values.tolist()
    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul[start:].values.tolist(), ManRiverNitrate=ManRiverNitrate[start:].values.tolist(),
        ManRiverAmmonia=ManRiverAmmonia[start:].values.tolist(),ManRiverP=ManRiverP[start:].values.tolist(), tanks=tanks.loc[tanks['time']>=RequestedSimDates[start]].values.tolist(),
        ManRiverFlows = list_results[start:].values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows[start:].values.tolist(),
        ManSewerFlows = ManSewerFlows[start:].values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates[start:].to_list(),
        ManStormdischargeFlows=ManStormdischargeFlows[start:].values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
        ManFoulToStormFlows=ManFoulToStormFlows[start:].values.tolist(),ManExcessWater=ManExcessWater[start:].values.tolist())
    #old version below, new(and work) above
    '''
    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul.values.tolist(), ManRiverNitrate=ManRiverNitrate.values.tolist(),
        ManRiverAmmonia=ManRiverAmmonia.values.tolist(),ManRiverP=ManRiverP.values.tolist(), tanks=tanks.values.tolist(),
        ManRiverFlows = list_results.values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows.values.tolist(),
        ManSewerFlows = ManSewerFlows.values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates.to_list(),
        ManStormdischargeFlows=ManStormdischargeFlows.values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
        ManFoulToStormFlows=ManFoulToStormFlows.values.tolist())
    '''

#########

'''
the below did not work, possibly because of trying to call vdr_send from within the same flask app
##the function below will update the inputs through the form, call vdr_send, and display the returned results
@app.route('/', methods=["GET", "POST"])
def index():

    #session['user'] = 'vdr'#needed??

    ######## trying giving some trial data
    #first lot for changes in RC
    _nodes=[3,5]
    _RC=[0.9,0.7]

    populationNodes=[4,6,7]
    PopulationValues=[1000, 1000000,100]#NB - actually a multiplier, lets not get confused

    #############end of the giving some data#######
    datafinal = [(prepare(_nodes)),(prepare(_RC)),prepare(populationNodes), prepare(PopulationValues)]

    #########now lets try to call vdr_send

    try:
        url2call='https://e96kri69.pythonanywhere.com/vdr_send'
        ret = requests.post(url2call, json=datafinal)

        r = ret.json()
        ManRiverFlows_ = (r['ManRiverFlows'])
        ManSewerFlows_ = (r['ManSewerFlows'])
        SimDates = (r['SimulationDates'])

        #now let's reconstruct a DF from an input:
        SimDates=pd.to_datetime(SimDates)
        ManRiverFlows=pd.DataFrame(ManRiverFlows_)
        ManRiverFlows.index=SimDates
        ManRiverFlows.columns=r['ManRiverDFcolumns']
        ManRiverFlows.set_index(ManRiverFlows.index)

        ###########end of trying to call vdr_send
        str2display='Below should be a table:'
        table2display=ManRiverFlows.to_html()

    except Exception as e:
        str2display='Something is not quite right;'
        str2display+=' and the error was ' + str(e)
        return str2display
    try:
        return render_template(FormURL, comments=str2display, table=table2display, PlaceHolder2try='Nothing yet', ManRiverFlows=ManRiverFlows_)
    except:
        return 'There seems to be a problem trying to do what was requested - please contact VK to debug'+str2display

    #return 'Just a dummy string to confirm this is alive'
'''
##########

##########
#This one will work with Oct msv version and accept a limited number of inputs, an return fewer results
@app.route('/vdr_SendDict', methods=["GET", "POST"])
#this will receive the data, run WSIMOD, and return the results
def GetDictToAPIreturnWSIMOD():
    # brings json data and returns it.
    data1 = request
    #return jsonify(data1)
    #new block insteaD OF THE OLD below
    data=ast.literal_eval(data1.json)#trying to reinstate the dictionary
    nodes_numbers_to_change=data['nodes_numbers_to_change']
    RC_to_change=data['RC_to_change']
    catchmentN4populationChange=data['catchmentN4populationChange']
    PopulationChange=data['PopulationChange']
    StartDate=data['StartDate']
    EndDate=data['EndDate']

    #end of new block

    RequestedSimDates = pd.date_range(StartDate,EndDate,freq='D')#this is a subset for what is currently available


    #develops a list of nodes to change for RC
    node_names_to_change = []
    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
        print('RC will change in: ', list_of_nodes[i][0])

    #develops a list of nodes for population change
    NodeNames4populationChange = []
    for ii in catchmentN4populationChange:
        NodeNames4populationChange.append(list_of_nodes[ii][0])
        print('and the population will change in: ', list_of_nodes[ii][0])

    list_results,ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows = callWSIMODfromFlask(node_names_to_change, RC_to_change,
                                                                        NodeNames4populationChange,PopulationChange,RequestedSimDates)
    ManRiverDFcolumns=list_results.columns.to_list()
    ManSewerDFcolumns=ManSewerFlows.columns.to_list()
    #return 'Got to here to return a string'
    return jsonify(ManRiverFlows = list_results.values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows.values.tolist(),
        ManSewerFlows = ManSewerFlows.values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates.to_list())





##########
@app.route('/vdr_send', methods=["GET", "POST"])
#this will receive the data, run WSIMOD, and return the results
def APIreturnWSIMOD():
    # brings json data and returns it.
    data1 = request
    print('this is request')
    print (data1)
    data = data1.json
    print('this is the final request after json')
    print (data)
    nodes_numbers_to_change = input_to_int(data[0])
    RC_to_change = input_to_float(data[1])
    catchmentN4populationChange=input_to_int(data[2])
    #PopulationChange=input_to_int(data[3])
    PopulationChange=input_to_float(data[3])
    StartDate=str(data[4])
    EndDate=data[5]
    RequestedSimDates = pd.date_range(StartDate,EndDate,freq='D')#this is a subset for what is currently available


    #develops a list of nodes to change for RC
    node_names_to_change = []
    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
        print('RC will change in: ', list_of_nodes[i][0])

    #develops a list of nodes for population change
    NodeNames4populationChange = []
    for ii in catchmentN4populationChange:
        NodeNames4populationChange.append(list_of_nodes[ii][0])
        print('and the population will change in: ', list_of_nodes[ii][0])
    print('I am in APIreturnWSIMOD() function')
    list_results,ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows = callWSIMODfromFlask(node_names_to_change, RC_to_change,
                                                                        NodeNames4populationChange,PopulationChange,RequestedSimDates)
    ManRiverDFcolumns=list_results.columns.to_list()
    ManSewerDFcolumns=ManSewerFlows.columns.to_list()

    return jsonify(ManRiverFlows = list_results.values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows.values.tolist(),
            ManSewerFlows = ManSewerFlows.values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates.to_list())

########
@app.route('/vdr_send2', methods=["GET", "POST"])
#this will receive the data, run WSIMOD, and return the results
#it is an enhanced version of the vdr_send end point, and is analogous to the vdr_SendDict2 endpoint
#but is designed to work with the 'vkrivtso.pythonanywhere' website forms
def EnhancedAPIreturnWSIMOD():
    # brings json data and returns it.
    data1 = request
    print('this is request')
    print (data1)
    data = data1.json
    print('this is the final request after json')
    print (data)
    if len(data[0])>=1:
        nodes_numbers_to_change = input_to_int(data[0])
    else: nodes_numbers_to_change=[]
    if len(data[1])>=1:
        RC_to_change = input_to_float(data[1])
    else:RC_to_change=[]

    catchmentN4populationChange=input_to_int(data[2])
    #PopulationChange=input_to_int(data[3])
    PopulationChange=input_to_float(data[3])
    StartDate=str(data[4])
    EndDate=data[5]
    RequestedSimDates = pd.date_range(StartDate,EndDate,freq='D')#this is a subset for what is currently available
    catchmentN4wiltPointChange=input_to_int(data[6])
    newWiltPointMultiplier=input_to_float(data[7])
    catchmentN4demandChange=input_to_int(data[8])
    NewPerCapitaDemand=input_to_float(data[9])
    if len(data[10])>1:
        PopulationGrowth=float(data[10])#NB use of float() instead of input_to_float (the latter produces a list)
    else:
        PopulationGrowth=1#i.e. no growth if the input left blank
    if len(data[11])>1:
        RainfallMultiplier=float(data[11])#NB use of float() here instead of input_to_float (the latter produces a list)
    else:
        RainfallMultiplier=1##i.e. no change in rainfall if the input left blank
    if len(data[12])>1:
        MinSimLength=int(data[12])#NB use of float() here instead of input_to_float (the latter produces a list)
    else:
        MinSimLength=DefaultVdrSimLength
    if len(data[13])>1:
        days2delete=int(data[13])#NB use of float() here instead of input_to_float (the latter produces a list)
    else:
        days2delete=DefaultDays2delete#

    #develops a list of nodes to change for RC
    node_names_to_change = []
    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
        print('RC will change in: ', list_of_nodes[i][0])

    #develops a list of nodes for population change
    NodeNames4populationChange = []
    for ii in catchmentN4populationChange:
        NodeNames4populationChange.append(list_of_nodes[ii][0])
        print('and the population will change in: ', list_of_nodes[ii][0])

    NodeNames4wiltPointChange=GetListOfNodeNamesFromTheirNumbers(catchmentN4wiltPointChange, list_of_nodes)
    NodeNames4demandChange=GetListOfNodeNamesFromTheirNumbers(catchmentN4demandChange, list_of_nodes)


    #list_results,ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows = callWSIMODfromFlask(node_names_to_change, RC_to_change,
    #                                                                   NodeNames4populationChange,PopulationChange,RequestedSimDates)

    ManFlowsDemand2foul, ManRiverNitrate, ManRiverAmmonia, ManRiverP,tanks, list_results, ManWWTPdischargeFlows,\
        ManSewerFlows, ManStormdischargeFlows,ManFoulToStormFlows, ManLandToOutletFlows, ManExcessWater=\
        callWSIMODfromFlaskEnhanced(node_names_to_change, RC_to_change,\
        NodeNames4populationChange,PopulationChange,\
        RequestedSimDates,RainfallMultiplier,\
        NodeNames4wiltPointChange, newWiltPointMultiplier,\
        NodeNames4demandChange, NewPerCapitaDemand, PopulationGrowth)

    asd=ManStormdischargeFlows.copy()#added in May2023
    asd.columns=ManLandToOutletFlows.copy().columns
    ManExcessWater=asd+ManLandToOutletFlows.copy()#added in May2023
    ManExcessWater.columns=nodes.copy().index[:-1]#added in May2023


    ManRiverDFcolumns=list_results.columns.to_list()
    ManSewerDFcolumns=ManSewerFlows.columns.to_list()
    ManWWTPdischargeDFcolumns=ManWWTPdischargeFlows.columns.to_list()

    #below is the bit added in May/June 2023 to cut the initial 'run-in' period
    if (len(RequestedSimDates)-MinSimLength)<=days2delete:
        start=max(0,len(RequestedSimDates)-MinSimLength)
    else:
        start=days2delete

    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul[start:].values.tolist(), ManRiverNitrate=ManRiverNitrate[start:].values.tolist(),
        ManRiverAmmonia=ManRiverAmmonia[start:].values.tolist(),ManRiverP=ManRiverP[start:].values.tolist(), tanks=tanks.loc[tanks['time']>=RequestedSimDates[start]].values.tolist(),
        ManRiverFlows = list_results[start:].values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows[start:].values.tolist(),
        ManSewerFlows = ManSewerFlows[start:].values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates[start:].to_list(),
        ManStormdischargeFlows=ManStormdischargeFlows[start:].values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
        ManFoulToStormFlows=ManFoulToStormFlows[start:].values.tolist(),ManExcessWater=ManExcessWater[start:].values.tolist())

'''
    #below- the previous return version (before the introduction of the run-in period
    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul.values.tolist(), ManRiverNitrate=ManRiverNitrate.values.tolist(),
            ManRiverAmmonia=ManRiverAmmonia.values.tolist(),ManRiverP=ManRiverP.values.tolist(), tanks=tanks.values.tolist(),
            ManRiverFlows = list_results.values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows.values.tolist(),
            ManSewerFlows = ManSewerFlows.values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates.to_list(),
            ManStormdischargeFlows=ManStormdischargeFlows.values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
            ManFoulToStormFlows=ManFoulToStormFlows.values.tolist(), ManExcessWater=ManExcessWater.values.tolist())
'''
##################end of the vdr_send2 end point

###################################Below are auxiliary functions#####################
def GetListOfNodeNamesFromTheirNumbers(nodes_numbers_to_change, list_of_nodes):
    #develops a list of nodes to change
    node_names_to_change = []
    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
    return node_names_to_change

########
#this function will be used with the enhanced (i.e. Nov version) API
def callWSIMODfromFlaskEnhanced(subcatchment_change = None, new_runoff_coef = None,
        catchmentsForPopulationChange=None,PopulationChange=None, dates=None,RainfallMultiplier=None,
        catchmentsForWiltPointChange=None, newWiltPointMultiplier=None,
        catchmentsForDemandChange=None, NewPerCapitaDemand=None, PopulationGrowth=None):

    data_dir = os.path.join(
        os.path.dirname(
                os.path.dirname(
                        os.path.abspath(__file__))),
        "data", "manchester")
    print('RainfallMultiplier='+ str(RainfallMultiplier))
    nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = mswNov.load_manchester(data_dir,dates,RainfallMultiplier)
    #nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = mswNov.load_manchester(data_dir,dates,2)


    #sim(x, nodes, arcs, land_node_info, input_dict,dates=DefaultSimDates)#where x is for the lags (number of days)
    #flows,tanks = msw.sim(x, nodes, arcs, land_node_info, input_dict,dates,wwtp_node_info,
    #                     subcatchment_change, new_runoff_coef, catchmentsForPopulationChange,PopulationChange)#from old version

    flows,tanks=mswNov.sim(x, nodes, arcs, land_node_info, input_dict,dates,wwtp_node_info,
            subcatchment_change,new_runoff_coef,
            catchmentsForPopulationChange,PopulationChange,
            catchmentsForWiltPointChange, newWiltPointMultiplier,
            catchmentsForDemandChange, NewPerCapitaDemand, PopulationGrowth)

    ManFlows=flows.pivot(index='time', columns='arc',values='flow')
    tanks.pivot(index='time', columns='node',values='storage')
    ###start insertion by VK on 20 Jul
    ManRiverFlows=pd.DataFrame()
    for item in arcs.name:
        ManRiverFlows[item]=ManFlows[item]
    #VK inserted the above  on Ed's request to simplify the matrix, and changed the return below
    #VK coded the below for Ed to easily summarise the flows to/from Waste water plants
    ##BD edit 2023-09-18
    ManSewerFlows=ManRiverFlows
    #pd.DataFrame()
    #for item in wwtp_node_info['uwwName']:
    #    item_='centralised_sewer-to-'+item
    #    ManSewerFlows[item_]=ManFlows[item_]
    #end edit

    ManFlowsDemand2foul=pd.DataFrame()
    #for item in land_node_info.index:
    #the above changed to below in Feb2023 to be in alfabet order (was causing trouble before)
    for item in land_node_info.index.sort_values():
        item_=item+'-demand-to-foul'
        ManFlowsDemand2foul[item_]=ManFlows[item_]

    ManWWTPdischargeFlows=pd.DataFrame()
    for item1,item2 in zip(wwtp_node_info['uwwName'],wwtp_node_info['WB_NAME']):
        item_=item1+'-to-'+item2
        ManWWTPdischargeFlows[item_]=ManFlows[item_]

    #VK under development: now for the storm flows:
    ManStormdischargeFlows=pd.DataFrame()
    #for item in land_node_info.index:
    #the above changed to below in Feb2023 to be in alfabet order (was causing trouble before)
    for item in land_node_info.index.sort_values():
        item_=item+'-storm-to-outlet'
        ManStormdischargeFlows[item_]=ManFlows[item_]

    #VK added below in Mar 2023 for the surface runoff:
    ManLandToOutletFlows=pd.DataFrame()
    for item in land_node_info.index.sort_values():
        item_=item+'-land-to-outlet'
        ManLandToOutletFlows[item_]=ManFlows[item_]

    asd=ManStormdischargeFlows.copy()#this bit added in May2023
    asd.columns=ManLandToOutletFlows.copy().columns
    ManExcessWater=asd+ManLandToOutletFlows.copy()#added in May2023
    ManExcessWater.columns=nodes.copy().index[:-1]


    #Now will deal with WQ
    ManPhosphate=flows.pivot(index='time', columns='arc',values='phosphate')
    ManRiverP=pd.DataFrame()
    for item in arcs.name:
        ManRiverP[item]=ManPhosphate[item]


    ManNitrate=flows.pivot(index='time', columns='arc',values='nitrate')
    ManRiverNitrate=pd.DataFrame()
    for item in arcs.name:
        ManRiverNitrate[item]=ManNitrate[item]

    ManAmmonia=flows.pivot(index='time', columns='arc',values='ammonia')
    ManRiverAmmonia=pd.DataFrame()
    for item in arcs.name:
        ManRiverAmmonia[item]=ManAmmonia[item]

    #VK addition in Jan 2023
    ManFoulToStormFlows=pd.DataFrame()
    #for item in land_node_info.index:
    for item in land_node_info.index.sort_values():

        item_=item+'-foul-to-storm'
        ManFoulToStormFlows[item_]=ManFlows[item_]




    #return ManRiverFlows, ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows#old Oct version
    return ManFlowsDemand2foul, ManRiverNitrate, ManRiverAmmonia, ManRiverP,tanks, ManRiverFlows, ManWWTPdischargeFlows,\
        ManSewerFlows, ManStormdischargeFlows, ManFoulToStormFlows, ManLandToOutletFlows, ManExcessWater


#########
#this function to be used with the basic October version of API
def callWSIMODfromFlask(subcatchment_change = None, new_runoff_coef = None,
                    catchmentsForPopulationChange=None,PopulationChange=None, dates=None):
#This function basically mimics the one called simulateAPIcall elsewhere
    data_dir = os.path.join(
        os.path.dirname(
                os.path.dirname(
                        os.path.abspath(__file__))),
        "data", "manchester")

    nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = msw.load_manchester(data_dir,dates)


    #sim(x, nodes, arcs, land_node_info, input_dict,dates=DefaultSimDates)#where x is for the lags (number of days)
    flows,tanks = msw.sim(x, nodes, arcs, land_node_info, input_dict,dates,wwtp_node_info,
                          subcatchment_change, new_runoff_coef, catchmentsForPopulationChange,PopulationChange)
    ManFlows=flows.pivot(index='time', columns='arc',values='flow')
    tanks.pivot(index='time', columns='node',values='storage')
    ###start insertion by VK on 20 Jul
    ManRiverFlows=pd.DataFrame()
    for item in arcs.name:
        ManRiverFlows[item]=ManFlows[item]
    #VK inserted the above  on Ed's request to simplify the matrix, and changed the return below
    #VK coded the below for Ed to easily summarise the flows to/from Waste water plants
    ##BD edit 2023-09-18
    ManSewerFlows=ManRiverFlows
    #pd.DataFrame()
    #for item in wwtp_node_info['uwwName']:
    #    item_='centralised_sewer-to-'+item
    #    ManSewerFlows[item_]=ManFlows[item_]
    #end edit
    ManWWTPdischargeFlows=pd.DataFrame()
    for item1,item2 in zip(wwtp_node_info['uwwName'],wwtp_node_info['WB_NAME']):
        item_=item1+'-to-'+item2
        ManWWTPdischargeFlows[item_]=ManFlows[item_]

    #VK under development: now for the storm flows:
    ManStormdischargeFlows=pd.DataFrame()
    #for item in land_node_info.index:
    #the above changed to below in Feb2023 to be in alfabet order (was causing trouble before)
    for item in land_node_info.index.sort_values():
        item_=item+'-storm-to-outlet'
        ManStormdischargeFlows[item_]=ManFlows[item_]


    return ManRiverFlows, ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows
def input_to_int(data):
    #edited by VK in Jan 2023
    if len(data)>=1:
        data_string = data.split(",")
        data_return = []
        for i in data_string:
            data_return.append(int(i))

    else:
        data_return=[]
    return data_return

def input_to_float(data):
    if len(data)>=1:
        data_string = data.split(",")
        data_return = []
        for i in data_string:
            data_return.append(float(i))
        return data_return
    else:
        return []

def prepare(listofdata):
    data = str(listofdata[0])
    for i in range (1,len(listofdata)):
        data=data + ',' + str(listofdata[i])
    return(data )


@app.route('/test', methods=["GET", "POST"])
def testForm():
    str2display='Would it display anything in here?  time.time()='
    str2display+=str(time.time())
    return str2display


############
#####the below will just run a specific example to display results, previously at https://e96kri69.pythonanywhere.com/vdr_hello
@app.route('/TestWSIMOD', methods=["GET", "POST"])
def TestHelloFromWSIMODflask():
    #str2display='Hello again! - from Flask inside WSIMOD scripts dir!'
    #ManRiverFlows_=[]#needed for debugging (alternative way of displaying)

    print('I am in TestHelloFromWSIMODflask() function')
    # initialises model information
    data_dir = os.path.join(
        os.path.dirname(
                os.path.dirname(
                        os.path.abspath(__file__))),
        "data", "manchester")
    nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info = msw.load_manchester(data_dir,dates)




    list_of_nodes = nodes.loc[nodes['type'] == 'catchment'].index
    df = pd.DataFrame(list_of_nodes)
    list_of_nodes = df.values.tolist()

    nodes_numbers_to_change = [23,22,35]#just an example
    # nodes_numbers_to_change=[]
    # for jj in range(1,44): nodes_numbers_to_change.append(jj)


    RC_to_change = [0.9,0.9,0.9]
    #RC_to_change = [0.1,0.1,0.1];


    catchmentN4populationChange=[20,22,35]#in those catchment population will be multiplied by PopulationChange
    PopulationChange=[1.2,1.2,1.2]#e.g. 1.2 is an increase of 20% relative to the preset value

    # RC_to_change=[]
    # for ii in range(0,44): RC_to_change.append(0.1)



    #develops a list of nodes to change for RC
    node_names_to_change = []

    for i in nodes_numbers_to_change:
        node_names_to_change.append(list_of_nodes[i][0])
        print('RC will change in: ', list_of_nodes[i][0])

    #develops a list of nodes for population change
    NodeNames4populationChange = []
    for ii in catchmentN4populationChange:
        NodeNames4populationChange.append(list_of_nodes[ii][0])
        print('and the population will change in: ', list_of_nodes[ii][0])

    list_results,ManWWTPdischargeFlows, ManSewerFlows, ManStormdischargeFlows = callWSIMODfromFlask(node_names_to_change, RC_to_change,
                                                                        NodeNames4populationChange,PopulationChange,dates)




    #str2display=list_results
    table2display=list_results.to_html()
    str2display='Below is a table of river flows in the upper Mersey subcatchments for the test simulation with preset parameters:'
    #return str2display
    return render_template(FormURL, comments=str2display, table=table2display, PlaceHolder2try='Nothing yet', ManRiverFlows=ManRiverFlows_)


'''
the below did not work, possibly because of trying to call vdr_send from within the same flask app
##the function below will update the inputs through the form, call vdr_send, and display the returned results
@app.route('/', methods=["GET", "POST"])
def index():

    #session['user'] = 'vdr'#needed??

    ######## trying giving some trial data
    #first lot for changes in RC
    _nodes=[3,5]
    _RC=[0.9,0.7]

    populationNodes=[4,6,7]
    PopulationValues=[1000, 1000000,100]#NB - actually a multiplier, lets not get confused

    #############end of the giving some data#######
    datafinal = [(prepare(_nodes)),(prepare(_RC)),prepare(populationNodes), prepare(PopulationValues)]

    #########now lets try to call vdr_send

    try:
        url2call='https://e96kri69.pythonanywhere.com/vdr_send'
        ret = requests.post(url2call, json=datafinal)

        r = ret.json()
        ManRiverFlows_ = (r['ManRiverFlows'])
        ManSewerFlows_ = (r['ManSewerFlows'])
        SimDates = (r['SimulationDates'])

        #now let's reconstruct a DF from an input:
        SimDates=pd.to_datetime(SimDates)
        ManRiverFlows=pd.DataFrame(ManRiverFlows_)
        ManRiverFlows.index=SimDates
        ManRiverFlows.columns=r['ManRiverDFcolumns']
        ManRiverFlows.set_index(ManRiverFlows.index)

        ###########end of trying to call vdr_send
        str2display='Below should be a table:'
        table2display=ManRiverFlows.to_html()

    except Exception as e:
        str2display='Something is not quite right;'
        str2display+=' and the error was ' + str(e)
        return str2display
    try:
        return render_template(FormURL, comments=str2display, table=table2display, PlaceHolder2try='Nothing yet', ManRiverFlows=ManRiverFlows_)
    except:
        return 'There seems to be a problem trying to do what was requested - please contact VK to debug'+str2display

    #return 'Just a dummy string to confirm this is alive'
'''
##########


