"""Start 8 separate service processes and gateway; Ctrl+C stops all children."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shared.config import PORTS, database_path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--service',choices=list(PORTS)+['gateway'])
    args=parser.parse_args()
    if not database_path().exists():
        sys.exit('Run python scripts/init_db.py --demo first.')
    names=[args.service] if args.service else list(PORTS)+['gateway']
    for name in names:
        port=PORTS.get(name,5000)
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0: sys.exit(f'Port {port} is already in use ({name}).')
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT);env['PYTHONUNBUFFERED']='1';env['PYTHONIOENCODING']='utf-8'
    (ROOT/'logs').mkdir(exist_ok=True)
    processes=[];logs=[]
    try:
        for name in names:
            folder='gateway' if name=='gateway' else name+'-service'
            log=open(ROOT/'logs'/f'{name}.log','a',encoding='utf-8');logs.append(log)
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            process=subprocess.Popen([sys.executable,str(ROOT/folder/'app.py')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
            processes.append((name,process))
        import requests
        deadline=time.monotonic()+45
        pending=set(names)
        while pending and time.monotonic()<deadline:
            for name,process in processes:
                if process.poll() is not None: raise RuntimeError(f'{name} exited. See logs/{name}.log.')
                if name in pending:
                    try:
                        if requests.get(f'http://127.0.0.1:{PORTS.get(name,5000)}/health',timeout=.5).ok: pending.remove(name)
                    except requests.RequestException: pass
            if pending: time.sleep(.3)
        if pending: raise RuntimeError('Services not ready: '+', '.join(pending))
        print('Ready: http://localhost:5000 | Service Swagger: http://localhost:5001/docs ... :5008/docs',flush=True)
        print('Press Ctrl+C to stop. Logs: logs/',flush=True)
        while True:
            for name,process in processes:
                if process.poll() is not None: raise RuntimeError(f'{name} exited unexpectedly. See logs/{name}.log.')
            time.sleep(1)
    except KeyboardInterrupt: print('Stopping services...')
    finally:
        for _,process in processes:
            if process.poll() is None: process.terminate()
        for _,process in processes:
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
        for log in logs: log.close()

if __name__=='__main__': main()
