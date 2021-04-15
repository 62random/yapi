import os
from typing import Optional, List

import databases
import sqlalchemy as sa
import yaml
from fastapi import Security, Depends, FastAPI, HTTPException
from fastapi.security.api_key import APIKeyQuery, APIKey
from pydantic import BaseModel

CONFIG = yaml.safe_load(open(os.environ["CONFIG_FILE"], 'r'))
API_KEY = os.environ["API_KEY"]
DATABASE = databases.Database(CONFIG["url"])
METADATA = sa.MetaData()
SA_TYPE = {
    "int": sa.Integer,
    "float": sa.Float,
    "bool": sa.Boolean,
    "str": sa.String
}

# This is here cause the SaveActions Plugin doesn't find
# this stuff in the code i have inside the exec() down there 😅
_ = Depends(), Optional, BaseModel, APIKey, List


# Generate a table with a given name + params and their python types
def gen_table(name, params):
    args = [name, METADATA, sa.Column("id", sa.Integer, primary_key=True)]
    args.extend([sa.Column(k, SA_TYPE[params[k]]) for k in params])

    return sa.Table(*args, extend_existing=True)


class Args:
    @classmethod
    def create(cls, params):
        params_str = ",".join(f"{k}: Optional[{params[k]}]" for k in params)
        exec(f"def fn(self, {params_str}): pass;\ncls.__init__ = fn")
        return cls


def endpoint_post(endpoint_name, endpoint_params):
    print(f"{endpoint_name}:")
    for k in endpoint_params:
        print(f"{k}: {endpoint_params[k]}")


api_key_query = APIKeyQuery(name="api_key")


async def get_api_key(api_key_query: str = Security(api_key_query)):
    if api_key_query == API_KEY:
        return api_key_query
    else:
        raise HTTPException(status_code=403)


app = FastAPI()


@app.on_event("startup")
async def startup():
    await DATABASE.connect()


@app.on_event("shutdown")
async def shutdown():
    await DATABASE.disconnect()


# Sorry about this mess, but here I'm dynamically defining
# the application's routes based on the loaded yaml config file
nlt = '\n\t'
for endpoint in CONFIG["endpoints"]:
    ep_params = CONFIG["endpoints"][endpoint]
    exec(f"""
{endpoint}_table = gen_table(endpoint, ep_params)    

class Record{endpoint.capitalize()}In(BaseModel):
\t{nlt.join([f"{k}: {ep_params[k]}" for k in ep_params])}

class Record{endpoint.capitalize()}(BaseModel):
\t{nlt.join(["id: int"] + [f"{k}: {ep_params[k]}" for k in ep_params])}

@app.post("/{endpoint}", response_model=Record{endpoint.capitalize()})
async def {endpoint}_post(record: Record{endpoint.capitalize()}In, api_key: APIKey = Depends(get_api_key)):
    endpoint_post(endpoint, ep_params)
    query = {endpoint}_table.insert().values({', '.join([f"{k}=record.{k}" for k in ep_params])})
    last_record_id = await DATABASE.execute(query)
    return {{** record.dict(), "id": last_record_id}}

@app.get("/{endpoint}", response_model=List[Record{endpoint.capitalize()}])
async def {endpoint}_get(api_key: APIKey = Depends(get_api_key)):
    query = {endpoint}_table.select()
    return await DATABASE.fetch_all(query)
""")

engine = sa.create_engine(
    CONFIG["url"],
    connect_args={"check_same_thread": False})
METADATA.create_all(engine)
