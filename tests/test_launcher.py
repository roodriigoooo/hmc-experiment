"""Exercise launcher isolation/port fallback without opening a socket."""
import unittest, tempfile, importlib.util, io, errno, os
from pathlib import Path
from unittest.mock import patch, Mock
from server import app

spec=importlib.util.spec_from_file_location('local_demo',Path(__file__).resolve().parents[1]/'scripts/local-demo.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

class LauncherTests(unittest.TestCase):
    def test_busy_port_uses_loopback_and_separate_synthetic_database(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dist').mkdir();(root/'dist/index.html').write_text('test')
            http=Mock(server_port=8127);http.serve_forever.side_effect=KeyboardInterrupt
            saved_store,saved_admin=app.STORE,app.ADMIN
            try:
                with patch.object(launcher,'ROOT',root),patch.object(launcher,'ThreadingHTTPServer',side_effect=[OSError(errno.EADDRINUSE,'busy'),http]) as server,patch.object(launcher.subprocess,'check_output',return_value='hmc-test\n'),patch('os.chdir'),patch('sys.argv',['local-demo.py']),patch.dict(os.environ,{'DATABASE_PATH':str(root/'do-not-open.sqlite'),'ADMIN_PASSWORD':'ignored-existing-secret','COOKIE_SECURE':'1'}),patch('sys.stdout',new_callable=io.StringIO) as output:
                    launcher.main()
                    self.assertEqual([c.args[0] for c in server.call_args_list],[('127.0.0.1',8000),('127.0.0.1',0)])
                    self.assertIn('http://127.0.0.1:8127/?join',output.getvalue())
                    self.assertNotEqual(app.ADMIN,'ignored-existing-secret');self.assertGreaterEqual(len(app.ADMIN),16)
                    self.assertFalse((root/'do-not-open.sqlite').exists())
                    with app.STORE.db() as db:
                        rows=list(db.execute('SELECT mode,synthetic,protocol FROM sessions'))
                        self.assertEqual([tuple(r) for r in rows],[('demo',1,'pilot-4-demo-hmc-test')])
                    http.server_close.assert_called_once()
            finally:app.STORE,app.ADMIN=saved_store,saved_admin
    def test_permission_error_is_not_treated_as_busy_port(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dist').mkdir();(root/'dist/index.html').write_text('test')
            with patch.object(launcher,'ROOT',root),patch.object(launcher,'ThreadingHTTPServer',side_effect=PermissionError(errno.EPERM,'blocked')) as server,patch('os.chdir'),patch('sys.argv',['local-demo.py']),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit) as ex:
                launcher.main()
            self.assertEqual(ex.exception.code,1);self.assertEqual(server.call_count,1);self.assertFalse((root/'data').exists())
