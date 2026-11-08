from shared.web import create_app


def test_health_detects_unreadable_database(tmp_path):
    app=create_app('resident')
    app.config['DATABASE_PATH']=str(tmp_path)  # A directory cannot be opened as a DB.
    response=app.test_client().get('/health')
    assert response.status_code==503
    assert response.json['database']=='unavailable'


def test_gateway_health_does_not_require_database(tmp_path):
    app=create_app('gateway')
    app.config['DATABASE_PATH']=str(tmp_path)
    assert app.test_client().get('/health').status_code==200
