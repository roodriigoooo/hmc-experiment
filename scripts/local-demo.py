#!/usr/bin/env python3
"""Start a local synthetic demo. Never reads DATABASE_PATH or ADMIN_PASSWORD."""
import argparse, errno, secrets, subprocess, sys
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000,help='Preferred loopback port; use a free port if busy')
    args=parser.parse_args()
    if not (ROOT/'dist/index.html').exists():parser.error('Build first: npm run build (or use npm run demo)')
    # Handler resolves static files relative to the repository, as does production.
    import os
    os.chdir(ROOT)
    os.environ.pop('COOKIE_SECURE',None)  # This launcher binds loopback HTTP only.
    from server import app
    from server.protocol import DEFAULT
    from server.store import Store
    try:
        try:http=ThreadingHTTPServer(('127.0.0.1',args.port),app.Handler)
        except OSError as ex:
            if ex.errno!=errno.EADDRINUSE:raise
            http=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    except OSError as ex:
        parser.exit(1,f'Could not start local server: {ex}\nRun from a local terminal that permits loopback HTTP servers.\n')
    build=subprocess.check_output([sys.executable,str(ROOT/'scripts/build-id.py')],text=True).strip()
    database=ROOT/'data/local-demo.sqlite'
    app.STORE=Store(str(database),build)
    app.ADMIN=secrets.token_urlsafe(24)
    version='pilot-4-demo-'+build
    with app.STORE.db() as db:exists=db.execute('SELECT 1 FROM protocols WHERE id=?',(version,)).fetchone()
    if not exists:app.STORE.create_protocol(DEFAULT|dict(version=version))
    session=app.STORE.create('demo',version,True)
    url=f'http://127.0.0.1:{http.server_port}'
    print(f'\nLocal synthetic demo: {url}/?join\nSession code: {session["code"]}\n\nResearcher page: {url}/admin\nTemporary researcher password: {app.ADMIN}\nDatabase: {database}\nBuild: {build}\nProtocol: {version}\n\nKeep this terminal open. Stop with Ctrl+C.\n',flush=True)
    try:http.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped; saved demo observations are retained.')
    finally:http.server_close()

if __name__=='__main__':main()
