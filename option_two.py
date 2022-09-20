import os
import json
import logging
import uuid
import time
import boto3

from logging.config import dictConfig
from api.core.models.logs import LogConfig
from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from typing import Callable
from user_agents import parse
from urllib.parse import parse_qs
from datetime import datetime, timedelta

LOGS_TABLE = os.environ['LOGS']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(LOGS_TABLE)



dictConfig(LogConfig().dict())
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

#OPTION 1 with logger
class CustomRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                body = await request.json()
            except:
                body = await request.body()

            logger.info({
                'uuid': f'{uuid.uuid4()}',
                'start_request': f'path={request.url.path}',
                'body': f'{body}'
            })

            response: Response = await original_route_handler(request)

            return response

        return custom_route_handler
      

#OPTION 2 for databases
class LoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                uuid_str = str(uuid.uuid4())
                header = dict(request.headers)
                if "uuid" in header.keys():
                    uuid_str = header["uuid"]

                user_agent = parse(request.headers["user-agent"])
                
                browser=user_agent.browser.version
                if len(browser) >=2:
                    browser_major,browser_minor = browser[0],browser[1]
                else:
                    browser_major,browser_minor =0,0

                
                user_os=user_agent.os.version
                if len(user_os) >=2:
                    os_major,os_minor = user_os[0],user_os[1]
                else:
                    os_major,os_minor =0,0

                # Request json
                body = await request.body()
                if len(body)!=0:
                    body=json.loads(body)
                else:
                    body=""

                request_json = {
                    "type":"request",
                    "uuid":uuid_str,
                    "env": os.environ.get("ENV"),
                    "region": os.environ.get("REGION"),
                    "name": os.environ.get("NAME"),
                    "method": request.method,
                    "useragent":
                    {
                        "family": user_agent.browser.family,
                        "major":  browser_major,
                        "minor":  browser_minor,
                        "patch":  user_agent.browser.version_string,
                            
                        "device": {
                                "family": user_agent.device.family,
                                "brand": user_agent.device.brand,
                                "model": user_agent.device.model,
                                "major": "0",
                                "minor": "0",
                                "patch": "0"
                            },
                        "os": {
                                "family": user_agent.os.family,
                                "major": os_major,
                                "minor": os_minor,
                                "patch": user_agent.os.version_string 
                            },
                    
                    },
                    "url": request.url.path,
                    "query": parse_qs(str(request.query_params)),
                    "body":body,
                    "length": request.get("content-length"),
                    'date': f'{datetime.now():%Y-%m-%d %H:%M:%S%z}'   

                }
                
                start_time = time.time()
                response = await original_route_handler(request)
                process_time = (time.time() - start_time) * 1000
                formatted_process_time = '{0:.2f}'.format(process_time)

                # Response json
                metrics_json = {
                    "type": "metrics",
                    "uuid": uuid_str,
                    "env": os.environ.get("ENV"),
                    "region": os.environ.get("REGION"),
                    "name": os.environ.get("NAME"),              
                    "method": request.method,
                    "status_code": response.status_code,
                    "url": request.url.path,
                    "query": parse_qs(str(request.query_params)),
                    "length": response.headers["content-length"],
                    "latency": formatted_process_time,
                    "date": f'{datetime.now():%Y-%m-%d %H:%M:%S%z}'   

                }
                
                ttl_date = datetime.now() + timedelta(90)
                
                try: 
                    item = {
                    'url' : f'{str(request_json["url"])}',
                    'method' : f'{request_json["method"]}',
                    'status_code' : f'{metrics_json["status_code"]}',
                    'latency': f'{metrics_json["latency"]}',
                    'date': f'{metrics_json["date"]}',
                    'ts_epoch': int(ttl_date.timestamp()),
                    'body': f'{str(request_json["body"])}',
                    'id': f'{request_json["uuid"]}',
                    'query': f'{metrics_json["query"]}'
                    }
                    table.put_item(Item=item)
                except Exception as exc:
                    print(exc)
                    pass

            except Exception as exc:

                body = await request.body()
                response = await original_route_handler(request)
                
                ttl_date = datetime.now() + timedelta(90)
                item = {
                'url' : f'{str(request.url.path)}',
                'method' : f'{request.method}',
                'status_code' : f'{response.status_code}',
                'date': f'{datetime.now():%Y-%m-%d %H:%M:%S%z}',
                'ts_epoch': int(ttl_date.timestamp()),
                'body': '',
                'id': f'{str(uuid.uuid4())}',
                "query": parse_qs(str(request.query_params))
                }
                table.put_item(Item=item)


            return response

        return custom_route_handler
