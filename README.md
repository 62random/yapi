# yapi
YAPI - Yaml API. Just a small project I use to create APIs automatically by specifying the endpoints in a YAML file, in small IoT/automation/DS projects.

The heavy lifting is done by [FastAPI](https://fastapi.tiangolo.com).

The generated endpoints are simply used to get or store data in any SQL database. A simple SQLite database can be used (as in the example), but a cloud-managed database is also a good idea :) 

<hr>

The example in [houses.yaml](https://github.com/62random/yapi/blob/main/example/houses.yaml) generates the following API:

![Generated API](img/api.png)