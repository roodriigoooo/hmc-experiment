"""Consistent online SQLite backup; output must be institutionally protected."""
import sqlite3,sys
from pathlib import Path
if sys.argv[1]=='--verify':
    with sqlite3.connect(f'file:{Path(sys.argv[2]).resolve()}?mode=ro',uri=True) as db:
        result=db.execute('PRAGMA integrity_check').fetchone()[0]
        print(result)
        if result!='ok':raise SystemExit(1)
else:
    src,dst=sys.argv[1:3]
    if Path(dst).exists():raise SystemExit('Destination already exists; choose a new backup path.')
    with sqlite3.connect(f'file:{Path(src).resolve()}?mode=ro',uri=True) as source,sqlite3.connect(dst) as target:source.backup(target)
    Path(dst).chmod(0o600)
    print('Consistent backup created.')
