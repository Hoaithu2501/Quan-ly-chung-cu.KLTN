import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

def database_path():
    path = Path(os.getenv('DATABASE_PATH', 'data/QLCC.db'))
    return path if path.is_absolute() else ROOT / path

def secret(name):
    value = os.getenv(name, '')
    if len(value) < 32:
        raise RuntimeError(f'{name} must have at least 32 characters. Run python scripts/init_db.py first.')
    return value

PORTS = {'auth':5001, 'resident':5002, 'billing':5003, 'parking':5004,
         'maintenance':5005, 'notification':5006, 'complaint':5007, 'chatbot':5008}

def service_url(name):
    return os.getenv(name.upper() + '_SERVICE_URL', f'http://127.0.0.1:{PORTS[name]}')
