import os
from aiohttp import web
from web_interface_clean import JapaneseTutorWeb
from cors_middleware import cors_middleware

app = web.Application(middlewares=[cors_middleware])

tutor_web = JapaneseTutorWeb()

app.router.add_get('/', tutor_web.index_handler)
app.router.add_post('/api/chat', tutor_web.chat_handler)
app.router.add_post('/api/upload-image', tutor_web.upload_image_handler)
app.router.add_static('/static', 'static')

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8081)

