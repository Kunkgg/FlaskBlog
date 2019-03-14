
import unittest
from flask import current_app
from app import create_app, db
from app.models import Role

config_type = 'testing'
# config_type = 'development'
# config_type = 'production'


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(config_type)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
