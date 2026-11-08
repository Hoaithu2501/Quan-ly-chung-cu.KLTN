"""Same-origin UI and API reverse proxy. No domain data access."""
from pathlib import Path
import requests
from flask import request, Response, send_from_directory
from shared.config import ROOT, PORTS, service_url
from shared.web import create_app as base_app, run, APIError

ROUTES={'auth':'auth','apartments':'resident','residents':'resident','contracts':'resident',
        'billing':'billing','parking':'parking','maintenance':'maintenance','notifications':'notification',
        'complaints':'complaint','chatbot':'chatbot'}

def create_app():
    app=base_app('gateway')

    @app.route('/api/<path:path>',methods=['GET','POST','PATCH','PUT','DELETE'])
    def proxy(path):
        service=ROUTES.get(path.split('/')[0])
        if service is None: raise APIError('Không tìm thấy API.',404)
        # Never forward internal service credentials from the public gateway.
        headers={key:request.headers[key] for key in ('Authorization','Content-Type','Idempotency-Key') if key in request.headers}
        try:
            upstream=requests.request(request.method,service_url(service)+'/api/'+path,
                params=request.args, data=request.get_data(),headers=headers,timeout=(3,45),allow_redirects=False)
        except requests.RequestException:
            raise APIError(f'Dịch vụ {service} chưa sẵn sàng. Vui lòng thử lại.',503)
        selected={key:upstream.headers[key] for key in ('Content-Type','Content-Disposition','Retry-After') if key in upstream.headers}
        return Response(upstream.content,status=upstream.status_code,headers=selected)

    @app.get('/api-status')
    def status():
        from concurrent.futures import ThreadPoolExecutor
        def check(name):
            try:
                response=requests.get(service_url(name)+'/health',timeout=2)
                return name,'ok' if response.ok else 'unavailable'
            except requests.RequestException: return name,'unavailable'
        with ThreadPoolExecutor(max_workers=8) as pool: results=dict(pool.map(check,PORTS))
        return {'services':results}

    @app.get('/')
    def index(): return send_from_directory(ROOT/'frontend','index.html')

    @app.get('/<path:filename>')
    def static_asset(filename): return send_from_directory(ROOT/'frontend',filename)

    return app

app=create_app()
if __name__=='__main__': run(app,5000)
