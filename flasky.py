
import os
from flask_migrate import Migrate
from app import create_app, db
from app.models import User, Role

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    from tests.test_basics import BasicsTestCase
    from tests.test_mail import EmailTestCase
    bt = BasicsTestCase()
    bt.setUp()
    tests = unittest.TestLoader().discover('tests')
    # tests = unittest.TestLoader().loadTestsFromModule('./tests/test_mail.py')
    # tests = unittest.TestLoader().loadTestsFromTestCase(EmailTestCase)
    unittest.TextTestRunner(verbosity=2).run(tests)
    bt.tearDown()
