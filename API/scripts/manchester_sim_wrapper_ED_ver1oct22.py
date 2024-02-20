# -*- coding: utf-8 -*-
"""
This script is for simulation of the WSIMOD upper Mersey catchment model;
an adaptation by VK of Barney's crane_sim_wrapper

"""
#wsimod packages
wsimod='~/mysite/wsimod/wsimod'
from wsimod.nodes.wtw import WWTW

from wsimod.nodes.waste import Waste
from wsimod.nodes.storage import EnfieldCatchWatGroundwater as Groundwater
from wsimod.nodes.storage import RiverReservoir as Reservoir
from wsimod.nodes.demand import ResidentialDemand as Demand
from wsimod.nodes.land import Land as Land
from wsimod.nodes.sewer import Sewer
from wsimod.nodes.sewer import EnfieldFoulSewer as FoulSewer
from wsimod.nodes.nodes import Node, Tank, QueueTank

from wsimod.arcs import Arc, DecayArc
from wsimod.core import constants

import geopandas as gpd
import pandas as pd
import numpy as np
import os
import time
from tqdm import tqdm
from math import log10
#from matplotlib import pyplot as plt

#pltVK="C:\KryoshaStuff\SpyderPython\wsimod-workshop-2021-enfield\scripts\orchestration\PlotFunctionsVK.py" #as pltVK
#import PlotFunctionsVK_versionJun2022 as pltVK

print('I am in the Manchester_sim_wrapper_ED_ver1Oct22 and have now done the imports!')


######Dafault Values#######
DefaultSimDates = pd.date_range('2011-01-01','2012-12-31',freq='D')
###Note that the values of most parameters are set within the functions######
### NB: Also see the section on Default Parameters within the Sim function below
#datesStr4fileName="_2000_2020_day_1_km.csv"
#datesStr4fileName="_1969_2020_day_1_km.csv"
datesStr4fileName="_2011_2012_day_1_km.csv"



######End Of Dafault Values####

#def sim(x, nodes, arcs, land_node_info, input_dict,dates=DefaultSimDates):
def sim(x, nodes, arcs, land_node_info, input_dict,dates=DefaultSimDates,wwtp_node_info=None,
        subcatchment_change = None, new_runoff_coef = None,catchmentsForPopulationChange=None,PopulationChange=None):


    """Define parameters
    """
    # constants.POLLUTANTS = ['phosphorus','phosphate','ammonia','solids','cod','nitrate','nitrite'] # All assume mg/l
    # constants.ADDITIVE_POLLUTANTS = ['phosphorus','phosphate','ammonia','solids','cod','nitrate','nitrite'] # All assume mg/l
    constants.NON_ADDITIVE_POLLUTANTS = [] # temperature or ph

    constants.POLLUTANTS = ['phosphate','ammonia','nitrate','solids'] # All assume mg/l
    constants.ADDITIVE_POLLUTANTS = ['phosphate','ammonia','nitrate','solids'] # All assume mg/l
    constants.FLOAT_ACCURACY = 1e-6

    #Define lag creator
    def create_lags(x):
        max_n_days = int(x) #days
        lags = np.logspace(0,np.log10(max_n_days + 1),max_n_days + 1)
        lags = np.diff(lags)
        lags = lags/lags.sum()
        lags = {x : y for x, y in zip(range(max_n_days), lags[::-1])}
        if len(lags) == 0:
            lags = {0 : 1}
        return lags

    area_label = 'wb_area'

    waste_name ="river-waste"#'Lower Mersey' # was 'thames' in the other WSIMOD setups
    #the above needs improving


    """Default params
    """
    #GW
    gw_depth = 0.5 #m
    sewer_infiltration_threshold = 0.5 #Sewer infiltration starts when GW active storage is greater than X% of capacity
    sewer_infiltration_amount = 0.1 #Percent of volume above threshold that gets pushed to sewers attached to groundwater node
    gw_residence_time = 50

    #Demands
    per_capita_demand = 0.15 #m^3/d
    demand_pol_dict = {'ammonia' : 15 * constants.MG_L_TO_KG_M3,
                        'nitrate' : 1 * constants.MG_L_TO_KG_M3,
                        'phosphate' : 10 * constants.MG_L_TO_KG_M3,
                        'solids' : 1000 * constants.MG_L_TO_KG_M3}

    #Foul sewer
    foul_timearea = create_lags(0)
    demand_excess = 1.25 #headroom for expected consumption (to account for peaks and infiltration)
    foul_node_split = 0.5 #% storage in nodes
    foul_pipe_split = 0.5 #% storage in pipes
    foul_storm_exchange = 0.95 #% capacity that must be exceed to start pushing to storm system

    #Storm sewer
    storm_timearea = create_lags(0) # what % of runoff takes how long (day) to leave sewer
    runoff_replacement = 5 * constants.MM_TO_M #daily mm of rain above which flooding will occur (kind of)
    storm_node_split = 0.5 #% storage in nodes
    storm_pipe_split = 0.5 #% storage in pipes

    #Land
    urban_quick_slow = 0.5
    urban_wilting_point = 0.01
    urban_infil = 10
    urban_evap_coef = 0.05
    urban_field_capacity = 0.1
    urban_percolation_coefficient = 0.5

    rural_quick_slow = 0.4
    rural_wilting_point = 0.2
    rural_infil = 50
    rural_evap_coef = 0.85
    rural_field_capacity = 0.15
    rural_percolation_coefficient = 0.5

    garden_quick_slow = 0.5
    garden_wilting_point = 0.15
    garden_infil = 50
    garden_evap_coef = 0.5
    garden_field_capacity = 0.15
    garden_percolation_coefficient = 0.5

    #Deposition in KG per m2
    urban_pol_dict = {'ammonia' : 30e-7,
                        'nitrate' : 60e-7,
                        'phosphate' : 10e-7,
                        'solids' : 900e-7}
    rural_pol_dict = {'ammonia' : 30e-7,
                        'nitrate' : 50e-7,
                        'phosphate' : 10e-7,
                        'solids' : 600e-7}
    garden_pol_dict = {'ammonia' : 30e-7,
                        'nitrate' : 50e-7,
                        'phosphate' : 10e-7,
                        'solids' : 600e-7}
    subsurface_lags = create_lags(2)

    #Decay parameters
    ammonia_land_decay_constant = 0.05
    ammonia_land_decay_exponent = 1.005
    ammonia_river_decay_constant = 0.05
    ammonia_river_decay_exponent = 1.01
    nitrate_land_decay_constant = 0.002
    nitrate_land_decay_exponent = 1.01
    nitrate_river_decay_constant = 0.05
    nitrate_river_decay_exponent = 1.005
    phosphate_land_decay_constant = 0.005
    phosphate_land_decay_exponent = 1.003
    phosphate_river_decay_constant = 0.05
    phosphate_river_decay_exponent = 1.001
    solids_land_decay_constant = 0.05
    solids_land_decay_exponent = 1.001
    solids_river_decay_constant = 0.05
    solids_river_decay_exponent = 1.01

    urban_percolation_coefficient = 0.5
    rural_percolation_coefficient = 0.5
    # Disable
    # def blockPrint():
    #     sys.stdout = open(os.devnull, 'w')

    # # Restore
    # def enablePrint():
    #     sys.stdout = sys.__stdout__
    #VK: The whole block above may be commented out if problems in debug
    # blockPrint() #VK: commented out on Barney's advise

    print("start_sim")
    start_time = time.time()



    land_decays = {'ammonia' : {'constant' : ammonia_land_decay_constant,
                                'exponent' : ammonia_land_decay_exponent},
                   'nitrate' : {'constant' : nitrate_land_decay_constant,
                                'exponent' : nitrate_land_decay_exponent},
                   'phosphate' : {'constant' : phosphate_land_decay_constant,
                                  'exponent' : phosphate_land_decay_exponent},
                   'solids' : {'constant' : solids_land_decay_constant,
                               'exponent' : solids_land_decay_exponent}}

    river_decays = {'ammonia' : {'constant' : ammonia_river_decay_constant,
                                 'exponent' : ammonia_river_decay_exponent},
                    'nitrate' : {'constant' : nitrate_river_decay_constant,
                                 'exponent' : nitrate_river_decay_exponent},
                    'phosphate' : {'constant' : phosphate_river_decay_constant,
                                   'exponent' : phosphate_river_decay_exponent},
                    'solids' : {'constant' : solids_river_decay_constant,
                                'exponent' : solids_river_decay_exponent}}

    """Create node objects
    """
    #Initiliase nodedict_type
    nodedict_type = {'outlet' : [],
                     'waste' : [],
                     'gw' : [],
                     'demand' : [],
                     'foul' : [],
                     'storm' : [],
                     'land' : [],
                     'reservoir' : [],
                     'wwtw' : []}


    for node_id in nodes.loc[nodes['type'] == 'catchment'].index:
        #Sub-catchment outlet
        nodedict_type['outlet'].append(Node(name = node_id))

        #GW
        nodedict_type['gw'].append(Groundwater(name = '{0}-gw'.format(node_id),
                                               area = land_node_info.loc[node_id, area_label],
                                               storage = land_node_info.loc[node_id, area_label] * gw_depth,
                                               sewer_infiltration_threshold = sewer_infiltration_threshold,
                                               sewer_infiltration_amount = sewer_infiltration_amount,
                                               decays = land_decays,
                                               residence_time = gw_residence_time,
                                               ))

        #Demand

        #VK: Now the population change bit under development; to confirm that this is the best place for it
        for ii in range (0, len(catchmentsForPopulationChange)):
            node_name = catchmentsForPopulationChange[ii]
            if node_id == node_name:
                PopulationMultiplier=PopulationChange[ii]
            else:
                PopulationMultiplier=1

        land_node_info.loc[node_id,'population']*=PopulationMultiplier


        #end of the population change bit under development

        pop = land_node_info.loc[node_id, 'population']
        nodedict_type['demand'].append(Demand(name = '{0}-demand'.format(node_id),
                                              population = pop,
                                              per_capita = per_capita_demand,
                                              pollutant_dict = demand_pol_dict))

        #Foul
        expected_consumption = pop * per_capita_demand * demand_excess
        nodedict_type['foul'].append(FoulSewer(node_storage = expected_consumption * foul_node_split,
                                                       pipe_storage = expected_consumption * foul_pipe_split,
                                                       pipe_timearea = foul_timearea,
                                                       name = '{0}-foul'.format(node_id),
                                                       storm_exchange = foul_storm_exchange,
                                                       )
                                     )

        #Storm
        impervious_area = land_node_info.loc[node_id,[area_label,'urban']].prod()
        expected_storm = impervious_area * runoff_replacement
        nodedict_type['storm'].append(Sewer(node_storage = expected_storm * storm_node_split,
                                            pipe_storage = expected_storm * storm_pipe_split,
                                            pipe_timearea = storm_timearea,
                                            name = '{0}-storm'.format(node_id)
                                            )
                                     )

        #Land
        #NB 'urban' is already with no 'gardens' BUT includes 'suburban'
        #see lines 207-217 in create_manchester
        rural_area = land_node_info.loc[node_id,[area_label,'rural']].prod()
        garden_area = land_node_info.loc[node_id,[area_label,'garden']].prod()
        rural_deposition_dict = {k : v * rural_area for k, v in rural_pol_dict.items()}
        urban_deposition_dict = {k : v * impervious_area for k, v in urban_pol_dict.items()}

        # ED's bit to modify the RC of a single node
        total_area = rural_area + impervious_area
        for i in range (0, len(subcatchment_change)):
            node_name = subcatchment_change[i]
            if node_id != node_name:
                runoff_coefficient = impervious_area / total_area
            else:
                runoff_coefficient = new_runoff_coef[i]

            impervious_area = runoff_coefficient * total_area
            rural_area = (1 - runoff_coefficient ) * total_area
        # end of RC stuff (VDR/ED)

        #Maybe in the future when the RC is adjusted,
        #we should improve the treatment of separate landusers, especially of the gardens



        surfaces = {'impervious' : {'quick_slow_split' : urban_quick_slow, #-
                               'wilting_point' : urban_wilting_point, #mm
                               'crop_coefficient' : urban_evap_coef, #%
                               'infiltration_t' : urban_infil, #mm
                               'pollutant_dict' : urban_deposition_dict,
                               'area' : impervious_area,
                               'capacity' : impervious_area * (urban_wilting_point + urban_field_capacity),
                               'field_capacity' : urban_field_capacity,
                               'decays' : land_decays,
                               'percolation_coefficient' : urban_percolation_coefficient},
                    'rural' : {'quick_slow_split' : rural_quick_slow, #-
                               'wilting_point' : rural_wilting_point, #mm
                               'crop_coefficient' : rural_evap_coef, #%
                               'infiltration_t' : rural_infil, #mm
                               'pollutant_dict' : rural_deposition_dict,
                               'area' : rural_area,
                               'capacity' : rural_area * (rural_wilting_point + rural_field_capacity),
                               'field_capacity' : rural_field_capacity,
                               'decays' : land_decays,
                               'percolation_coefficient' : rural_percolation_coefficient},
                    'garden' : {'quick_slow_split' : garden_quick_slow, #-
                               'wilting_point' : garden_wilting_point, #mm
                               'crop_coefficient' : garden_evap_coef, #%
                               'infiltration_t' : garden_infil, #mm
                               'pollutant_dict' : garden_pol_dict,
                               'area' : garden_area,
                               'capacity' : garden_area * (garden_wilting_point + garden_field_capacity),
                               'field_capacity' : garden_field_capacity,
                               'decays' : land_decays,
                               'percolation_coefficient' : garden_percolation_coefficient}}
        nodedict_type['land'].append(Land(surfaces = surfaces.copy(),
                                            name = '{0}-land'.format(node_id),
                                            data_input = 'precipitation',
                                            subsurface_timearea = subsurface_lags)
                                             )

    ###new megafoul sewer node creation bit; NB a bit preliminary - to improve once UU sends the data#####
    nodedict_type['foul'].append(FoulSewer(node_storage = 1e12,
                                                   pipe_storage = 1e12,
                                                   pipe_time=0,
                                                   pipe_timearea = {0:1},
                                                   name = 'centralised_sewer',
                                                   storm_exchange = foul_storm_exchange,
                                                   )
                                 )
    #nb the deliberately over huge number for the pipe_storage and node_storage
    #pipe_timearea {0:1} above means that 100% will travel at the same time step, i.e. instantaneously
    ##########end of  megafoul sewer node creation bit#####

    ###now another addition related to the new foul sewer node
    wwtw_process_multipliers = {'phosphate' : 1, 'ammonia' : 0.05, 'nitrate' : 20, 'solids' : 0.1}
    #SRP unchanged, but NOx hugely increase after mixing, whilst ammonia and solids decrease
    #wwtw_process_multipliers depends on specific pollutants, hence reqires improvement
    #it basically is related to what happens to constants.ADDITIVE_POLLUTANTS
    stormwater_storage_multiplier=2#to allow for bigger storage just in case
    wwtw_throughput_multiplier=2#to allow for bigger throughpu just in case

    for idx, wwtw in wwtp_node_info.iterrows():
        population_served = wwtw.uwwCapacit
        expected_foul_water = per_capita_demand * population_served
        nodedict_type['wwtw'].append(WWTW(name = wwtw.uwwName,
                                          stormwater_storage_capacity = expected_foul_water * stormwater_storage_multiplier,
                                          treatment_throughput_capacity = expected_foul_water * wwtw_throughput_multiplier,
                                          process_multiplier = wwtw_process_multipliers
                                          )
                                     )
    ###end of another addition related to the new foul sewer node



    for node_id in nodes.loc[nodes['type'] == 'reservoir'].index:
        nodedict_type['reservoir'].append(Reservoir(name = node_id,
                                                    storage = nodes.loc[node_id, 'capacity'],
                                                    area = nodes.loc[node_id, 'surface_area'],
                                                    environmental_flow = nodes.loc[node_id, 'environmental_flow']))

    nodedict_type['waste'].append(Waste(name = waste_name))




    #Create nodelist and nodedict
    nodelist = [y for x in nodedict_type.values() for y in x]
    nodedict = {x.name : x for x in nodelist}

    #Assign input data
    for node in nodelist:
        if (node.__class__ not in [Waste, Reservoir]) & (node.name != 'distribution') :
            #node_id = node.name.split('-')[0]
            #VK considered commenting the above to avoid the split of names  (long names are more descriptive)
            node.data_input_dict = input_dict[node_id]
        # elif (node.name == 'Brent Reservoir'):
        #     node.data_input_dict = input_dict['Lower Brent']
        #the above commented out as irrelevant but for now kept for reference

    """Create arcs
    """
    #Create arcs between catchments
    arclist = []
    for idx, arc in arcs.iterrows():
        arclist.append(DecayArc(in_port = nodedict[arc.in_port],
                             out_port = nodedict[arc.out_port],
                             name = arc['name'],
                             decays = river_decays))

    #Simplify arc creating
    def seek_node(node_id,type_):
        if type_ == 'outlet':
            return nodedict[node_id]
        else:
            return nodedict['{0}-{1}'.format(node_id,
                                             type_)]

    def arc_between(node_id, type_in, type_out):
        return Arc(in_port = seek_node(node_id,
                                       type_in),
                   out_port = seek_node(node_id,
                                        type_out),
                   name = '{0}-{1}-to-{2}'.format(node_id,
                                                  type_in,
                                                  type_out)
                   )



    #Create physical water cycle arcs
    for node_id in nodes.loc[nodes['type'] == 'catchment'].index:
        arclist.append(arc_between(node_id, 'land', 'storm')) #Standard runoff to sewer
        arclist.append(arc_between(node_id, 'demand', 'foul')) #Standard household waste drainage
        arclist.append(arc_between(node_id, 'land', 'gw')) #Hydrological recharge
        arclist.append(arc_between(node_id, 'gw', 'outlet')) #Baseflow/groundwater
        arclist.append(arc_between(node_id, 'storm', 'outlet')) #Standard storm sewer draining to rivers
        arclist.append(arc_between(node_id, 'gw', 'foul')) #Infiltration into foul network
        arclist.append(arc_between(node_id, 'gw', 'storm')) #Infiltration into storm network
        arclist.append(arc_between(node_id, 'foul', 'storm')) #Foul-storm exchange
        arclist.append(arc_between(node_id, 'land', 'outlet')) #Surface runoff
        arclist.append(Arc(in_port = seek_node(node_id, 'foul'),
                           out_port = nodedict['centralised_sewer'],
                           name = '{0}-foul-to-waste'.format(node_id)))
        #NB in the above the outport name was changed because of the creation of megasewer node
        #the old line was:   out_port = nodedict[waste_name],


    ###new code for creation of arcs from the centralised sewer to the treatment plants, and whence to outlets
    for idx, wwtw in wwtp_node_info.iterrows():

        arclist.append(Arc(in_port = nodedict['centralised_sewer'],
                                      out_port = nodedict[wwtw.uwwName],
                                      preference = wwtw.uwwCapacit,
                                      name='centralised_sewer-to-{0}'.format(wwtw.uwwName)))#VK added  names as was causing trouble
        #the variable 'preference' above ensures that the sewage from the megasewer node is pushed (distributed) to
        #the spesific WWTPs proportionally to their capacity

        arclist.append(Arc(in_port = nodedict[wwtw.uwwName],
                                      out_port = seek_node(wwtw.WB_NAME, 'outlet'),
                                      name='{0}-to-{1}'.format(wwtw.uwwName, wwtw.WB_NAME)))#VK added  names as was causing trouble
        #also VK subsequently changed the 'outlet' to wwtw.WB_NAME in the above  line
    ##end for the bit of creation of arcs from the centralised sewer to the treatment plants, and whence to outlets

    for node_id in nodes.loc[nodes.downstream_id == 'outlet'].index:
        arclist.append(Arc(in_port = seek_node(node_id, 'outlet'),
                           out_port = nodedict[waste_name],
                           name = '{0}-to-waste'.format(node_id)))

    #Run simulation
    flows = []
    tanks = []
    node_mb = []


    #enablePrint()#maybe commented out?
    mb_e = False
    for date in tqdm(dates):
    # for date in dates:
        #Tell every node what day it is
        for node in nodelist:
            node.t = date

        #Create demand (gets pushed to sewers)
        for node in nodedict_type['demand']:
            node.create_demand()

        #Create runoff (impervious gets pushed to sewers, pervious to groundwater)
        for node in nodedict_type['land']:
            node.create_runoff()

        #Discharge sewers (pushed to other sewers or WWTW)
        for node in nodedict_type['foul']:
            if node.name=='centralised_sewer':
                flag=1 #basically do nothing
            node.make_discharge()
        for node in nodedict_type['storm']:
            node.make_discharge()
        #below is a hack on 27 Jul - to deal with later
        nodedict['centralised_sewer'].make_discharge()


        #below is a new cycle created on 20 Jul 2022 related to the new megasewer:
        for node in nodedict_type['wwtw']:
            node.calculate_discharge()
            node.make_discharge()

        #end of the new cycle created on 20 Jul 2022 related to the new megasewer:

        #Discharge GW
        for node in nodedict_type['gw']:
            node.distribute()

        #Satisfy base flows
        for node in nodedict_type['reservoir']:
            node.satisfy_environmental()

        sys_in = nodelist[0].empty_vqip()
        sys_out = nodelist[0].empty_vqip()
        sys_ds = nodelist[0].empty_vqip()
        for node in nodelist:
            # print(node.name)
            in_, ds_, out_ = node.node_mass_balance()

            temp = {'name' : node.name,
                    'time' : date}
            for lab, dict_ in zip(['in','ds','out'], [in_, ds_, out_]):
                for key, value in dict_.items():
                    temp[(lab, key)] = value
            node_mb.append(temp)

            for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                sys_in[v] += in_[v]
                sys_out[v] += out_[v]
                sys_ds[v] += ds_[v]

        for v in constants.ADDITIVE_POLLUTANTS + ['volume']:

            largest = max(sys_in[v], sys_out[v], sys_ds[v])

            if largest > constants.FLOAT_ACCURACY:
                magnitude = 10**int(log10(largest))
                in_10 = sys_in[v] / magnitude
                out_10 = sys_out[v] / magnitude
                ds_10 = sys_ds[v] / magnitude
            else:
                in_10 = sys_in[v]
                ds_10 = sys_out[v]
                out_10 = sys_ds[v]
                if (in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                #VK changed the below (was the legacy of catchwat) to above on Barney's advise late Aug 22
                #if (sys_in[v] - sys_ds[v] - sys_out[v]) > constants.FLOAT_ACCURACY:
                    mb_e = True
                    print("system mass balance error for " + v + " of " + str(sys_in[v] - sys_ds[v] - sys_out[v]))

        #Store results
        for arc in arclist:
            flows.append({'arc' : arc.name,
                          'flow' : arc.flow_out,
                          'time' : date})
            for pol in constants.POLLUTANTS:
                flows[-1][pol] = arc.vqip_out[pol]

        for node in nodelist:
            for prop in dir(node):
                prop = node.__getattribute__(prop)
                if (prop.__class__ == Tank) | (prop.__class__ == QueueTank):
                    tanks.append({'node' : node.name,
                                  'time' : date,
                                  'storage' : prop.storage['volume']})

        for node in nodelist:
            node.end_timestep()

        for arc in arclist:
            arc.end_timestep()


    print("sim_duration: %s seconds" % (time.time() - start_time))
    #enablePrint()#maybe commented out?
    flows = pd.DataFrame(flows)
    tanks = pd.DataFrame(tanks)
    # node_mb = pd.DataFrame(node_mb)
    return flows, tanks

def load_manchester(data_dir,dates):
    #Load and format data; NB differences with crane
    #PARAMETER dates here needed for filtering off extra (redundant) data in the met files
    full_df = {}
    for var in ['rainfall','tasmin','tasmax','et0']:
        #df = pd.read_csv(os.path.join(data_dir,"processed" , "{0}_2011_2012_mon_1_km.csv".format(var)))
        #df = pd.read_csv(os.path.join(data_dir,"processed" , "{0}_2011_2012_day_1_km.csv".format(var)))
        #df = pd.read_csv(os.path.join(data_dir,"processed" , "{0}_2000_2020_day_1_km.csv".format(var)))
        #this moved into the inputs#datesStr4fileName="_2000_2020_day_1_km.csv"
        Str4fileName="{0}".format(var)+datesStr4fileName
        df = pd.read_csv(os.path.join(data_dir,"processed" , Str4fileName))
        #the above and below 4 otladka by VK, now dates are in Str4fileName  defined in input section
        #df = pd.read_csv(os.path.join(data_dir,"processed" , "{0}_2000_2020_day_1_km_aggregated.csv".format(var)))
        #df = df.rename(columns = {'time' : 'date'})#redundant?
        #Format
        #df.date = pd.to_datetime(df.date).dt.date
        '''
        NB: the original line of code above had to be changed on Barney's advice to the ones immediately below this comment because
        the 'dates' that we are iterating over in the enfield_sim_wrapper.py/sim are defined by 'pd.date_range'.
        This produces a pandas datetime object. Though what your date keys were is a standard python datetime object.
        For some reason VK's pandas when we do 'dt.date' produces the python datetime, while Barney's produces pandas datetime.
        Maybe these are different because we have different versions of pandas installed. In any case, even if the date is
        the same, the objects are different, and so they can't be used as keys in 'input_dict'
        '''
        df.date = pd.to_datetime(pd.to_datetime(df.date).dt.date)
        df = df.set_index('date')
        #df.loc[df.index>'2020-12-22']

        df=df.loc[df.index>=dates[0]]
        df=df.loc[df.index<=dates[-1]]
        #VK: the above 2 lines will get rid of extra dates
        full_df[var] = df
    full_df['tas'] = (full_df['tasmax'] - full_df['tasmin']) / 2 + full_df['tasmin']

    full_df['tas']['variable'] = 'temperature'
    full_df['rainfall']['variable'] = 'precipitation'
    full_df['et0']['variable'] = 'et0'
    full_df = pd.concat([full_df['tas'], full_df['rainfall'], full_df['et0']])

    input_dict = {}
    for col in full_df.columns.drop('variable'):
        df = full_df[[col,'variable']].reset_index()
        input_dict[col] = df.set_index(['variable','date'])[col].to_dict()

    #Load geospatial data
    nodes = gpd.read_file(os.path.join(data_dir, "raw","Manchester_trynodes_WSIMOD.csv"))
    nodes = nodes.pivot(index = 'node', columns='parameter', values = 'value')
    nodes = nodes.apply(pd.to_numeric, errors='coerce').fillna(nodes)

    arcs = gpd.read_file(os.path.join(data_dir, "processed","arcs.geojson"))
#    land_node_info = gpd.read_file(os.path.join(data_dir, "processed","landuse.geojson")).set_index('wb_name')
    land_node_info = gpd.read_file(os.path.join(data_dir, "processed","landuse.geojson")).set_index('WB_NAME')
    wwtp_node_info = gpd.read_file(os.path.join(data_dir, "processed","classified_wwtw.geojson"))

    wims_fid = os.path.join(data_dir, "processed", "wq_samples.csv")
    wq = pd.read_csv(wims_fid)
    wq.date_ = pd.to_datetime(wq.date_)

    return nodes, arcs, land_node_info, input_dict, wq, wwtp_node_info


