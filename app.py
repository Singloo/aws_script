from sanic import Sanic
from sanic.response import json,text

app = Sanic('wechat_service')


@app.get('/')
async def main_route(request):
    print(request)
    return text('hello')

