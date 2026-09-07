"""Exercise the local folder action with a real HTTP server and a mocked desktop."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import library_server as library

class StorageOpenTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),library.Handler)
        self.server.archive=library.Archive(self.root,library.SKILL_ROOT)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.opener=patch.object(library,'open_learning_directory',return_value={'status':'requested','message':'Requested'}).start()
        self.addCleanup(patch.stopall)
    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
    def request(self,body='{}',headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        standard={'Content-Type':'application/json','X-Coach-Token':self.server.archive.open_token}
        standard.update(headers or {})
        c.request('POST','/api/storage/open',body,standard)
        r=c.getresponse();result=(r.status,json.loads(r.read()));c.close();return result
    def test_valid_request_opens_only_bound_root(self):
        status,result=self.request(headers={'Origin':f'http://127.0.0.1:{self.server.server_port}'})
        self.assertEqual(status,200);self.assertEqual(result['status'],'requested')
        self.opener.assert_called_once_with(self.root)
    def test_foreign_origin_host_and_missing_token_do_not_open(self):
        for headers in [{'Origin':'https://foreign.example'},{'Host':'foreign.example'},
                        {'Host':'127.0.0.1:1'},{'X-Coach-Token':''}]:
            self.assertEqual(self.request(headers=headers)[0],403)
        self.opener.assert_not_called()
    def test_arbitrary_path_and_bad_bodies_do_not_open(self):
        for body in ['{"path":"/fictional/other"}','[]','null','bad',' '*129]:
            self.assertEqual(self.request(body)[0],400)
        self.opener.assert_not_called()
    def test_desktop_failure_has_no_success_claim(self):
        self.opener.side_effect=OSError('internal process detail')
        status,result=self.request()
        self.assertEqual(status,400);self.assertNotIn('status',result)
        self.assertNotIn('internal process detail',result['error'])

if __name__=='__main__':unittest.main()
