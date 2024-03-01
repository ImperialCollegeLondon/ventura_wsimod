
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import ast
#import sys
import os
import pandas as pd
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
    file_dir = Path(__file__).parent.parent / 'data' / 'ui_calls'
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

    #tanks=tanks.loc[tanks['time']>=RequestedSimDates[start]].values.tolist()
    return jsonify(ManFlowsDemand2foul=ManFlowsDemand2foul[start:].values.tolist(), ManRiverNitrate=ManRiverNitrate[start:].values.tolist(),
        ManRiverAmmonia=ManRiverAmmonia[start:].values.tolist(),ManRiverP=ManRiverP[start:].values.tolist(), tanks=tanks.loc[tanks['time']>=RequestedSimDates[start]].values.tolist(),
        ManRiverFlows = list_results[start:].values.tolist(), ManRiverDFcolumns=ManRiverDFcolumns, ManWWTPdischargeFlows = ManWWTPdischargeFlows[start:].values.tolist(),
        ManSewerFlows = ManSewerFlows[start:].values.tolist(), ManSewerDFcolumns=ManSewerDFcolumns,SimulationDates=RequestedSimDates[start:].to_list(),
        ManStormdischargeFlows=ManStormdischargeFlows[start:].values.tolist(), ManWWTPdischargeDFcolumns=ManWWTPdischargeDFcolumns,
        ManFoulToStormFlows=ManFoulToStormFlows[start:].values.tolist(),ManExcessWater=ManExcessWater[start:].values.tolist())
    #old version below, new(and work) above
  


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

