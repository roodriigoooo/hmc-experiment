"""Content fingerprint for a built application; no data/configuration secrets read."""
import hashlib
from pathlib import Path
h=hashlib.sha256()
for folder,pattern in [('server','*.py'),('dist','**/*')]:
    for p in sorted(Path(folder).glob(pattern)):
        if p.is_file():h.update(str(p).encode());h.update(p.read_bytes())
print('hmc-'+h.hexdigest()[:16])
