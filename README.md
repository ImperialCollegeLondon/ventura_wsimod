# ventura_wsimod
This repository contains the code for an old version of WSIMOD used in the VENUTRA project

## Install
- Download repo
- Navigate to directory
- `pip install .`

## Test
- Navigate to directory
- `pytest`
- You will get a bunch of warnings about zero losses, you can ignore these.

## Serve locally
- Navigate to: `ventura/scripts`
- `flask run`
- If you installed `curl` via `conda` on a windows machine, you can use the command in `ventura/scripts/example_curl_call.txt`, otherwise you can see the [Swagger UI](https://britishgeologicalsurvey.github.io/ventura-swagger-docs/#/Vladimir/vdr_SendDict2).
