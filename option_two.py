# import boto3
import pytz,time,uuid,json,os,logging

from requests import Session
from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
from user_agents import parse
from urllib.parse import parse_qs
from datetime import datetime

LOGS_TABLE = os.getenv('LOGS_TABLE')
user = os.getenv('ES_USER')
passwd = os.getenv('ES_PASSWD')
base_url = os.getenv('ES_URL')

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

class LoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request_body = {}
            try:
                uuid_str = str(uuid.uuid4())
                header = dict(request.headers)
                if "uuid" in header.keys():
                    uuid_str = header["uuid"]

                # Request json
                body = await request.body()
                if len(body) != 0:
                    try:
                        body = json.loads(body)
                    except:
                        body = body
                        logger.warn(f'Not JSON body: {body}')
                else:
                    body = {}
                request_body = body
                
                tz = pytz.timezone('America/Sao_Paulo')
                date_now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                
                user = _get_user(request)
                
                request_json = {
                    "type": "request",
                    "uuid": uuid_str,
                    "env": os.environ.get("ENV"),
                    "region": os.environ.get("REGION"),
                    "name": os.environ.get("NAME"),
                    "method": request.method,
                    "url": request.url,
                    "query": parse_qs(str(request.query_params)),
                    "body": body,
                    "length": request.get("content-length"),
                    'date': date_now
                }

                start_time = time.time()
                response = await original_route_handler(request)
                process_time = (time.time() - start_time) * 1000
                formatted_process_time = float('{0:.2f}'.format(process_time))

                tz = pytz.timezone('America/Sao_Paulo')
                date_now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S.000Z")

                # Response json
                metrics_json = {
                    "type": "metrics",
                    "uuid": uuid_str,
                    "env": os.environ.get("ENV"),
                    "region": os.environ.get("REGION"),
                    "name": os.environ.get("NAME"),
                    "method": request.method,
                    "status_code": response.status_code,
                    "url": request.url,
                    "query": parse_qs(str(request.query_params)),
                    "length": response.headers["content-length"],
                    "latency": formatted_process_time,
                    "date": date_now,
                    "body": json.loads(response.__dict__['body'].decode())

                }

                item = {
                    'url': f'{str(request_json["url"])}',
                    'method': f'{request_json["method"]}',
                    'status_code': f'{metrics_json["status_code"]}',
                    'latency': metrics_json["latency"],
                    'date': f'{metrics_json["date"]}',
                    'request': {"body":request_json["body"]},
                    'response': {"body":metrics_json['body']},
                    'id': f'{request_json["uuid"]}',
                    'query': f'{metrics_json["query"]}',
                    'request_ip': request.client.host,
                    'email':user
                } 
            except Exception as e:
                tz = pytz.timezone('America/Sao_Paulo')
                date_now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                user = _get_user(request)
                                
                item = {
                    'url': f'{str(request.url)}',
                    'method': f'{request.method}',
                    'status_code': 500,
                    'latency': 0,
                    'date': date_now,
                    'request': {"body":request_body}, 
                    'response': {"body":{"Exception":f"APP EXCEPTIONS: {e}"}}, 
                    'id': f'{str(uuid.uuid4())}',
                    "query": f'{parse_qs(str(request.query_params))}',
                    'request_ip': request.client.host,
                    'email':user
                }

            _put_item(item,item["id"])
            logger.warn(item)
            response = await original_route_handler(request)
            
            return response

        return custom_route_handler
    

def _put_item(item:dict,document_id):
    if not base_url:
        print('None ES_URL variable defined')
    else:
        url = f"{base_url}/{LOGS_TABLE}/_doc/{document_id}"
        auth = (user, passwd)
        session = Session()
        session.auth = auth
        
        response = session.put(url, json=item)
        if response.status_code == 201:
            print("Document created successfully!")
        else:
            print(f"Error creating document: {response.text}")

def _get_user(request):
    if request.headers.get("Authorization"):
        cred = request.headers.get("Authorization").replace('Bearer ','')
        auth_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=cred)
        user = get_email(auth_credentials)
    else:
        user = 'NoneToken'
    return user
