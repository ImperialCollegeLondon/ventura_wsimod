from ventura.scripts.app import app
import json
from pathlib import Path
def test_api():
    app.testing = True
    client = app.test_client()
    response = client.post('/vdr_SendDict2', json = {"nodes_numbers_to_change": 
                                                     [30, 14, 40, 7, 28, 25], 
                                                     "RC_to_change": 
                                                     [0.2, 0.2, 0.2, 0.2, 0.2, 0.2], 
                                                     "catchmentN4populationChange": 
                                                     [30, 14, 40, 7, 28, 25], 
                                                     "PopulationChange": 
                                                     [1, 1, 1, 1, 1, 1], 
                                                     "StartDate": "2011-11-30", 
                                                     "EndDate": "2012-01-30", 
                                                     "RainfallMultiplier": 1, 
                                                     "PopulationGrowth": 1, 
                                                     "catchmentN4wiltPointChange": [], 
                                                     "newWiltPointMultiplier": [], 
                                                     "catchmentN4demandChange": 
                                                     [30, 14, 40, 7, 28, 25], 
                                                     "NewPerCapitaDemand": 
                                                     [0.1086, 0.1086, 0.1086, 0.1086, 0.1086, 0.1086], 
                                                     "days2delete": 100, 
                                                     "MinSimLength": 2})
    assert response.status_code == 200

    output_results = response.data.decode('utf-8')
    output_results = json.loads(output_results)
    with open(Path(__file__).parent / 'test_data.json', 'r') as f:
        test_results = json.load(f)
    assert output_results == test_results

    