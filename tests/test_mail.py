
import unittest
from app.email import send_email


class EmailTestCase(unittest.TestCase):
    def test_send_email(self):
        try:
            send_email('goukun07@qq.com', 'TEST Flask-mail', 'mail/test')
        except:
            self.assertTrue(False)
        else:
            self.assertTrue(True)