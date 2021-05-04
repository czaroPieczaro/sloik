from flask_testing import TestCase
import unittest

from application import app, db, Jar
import mock


class BaseTestCase(TestCase):
    """A base test case."""

    def create_app(self):
        app.config.from_object('config.TestConfig')
        return app

    def setUp(self):
        db.create_all()
        jar = Jar(currency='BTC')
        db.session.add(jar)
        db.session.commit

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class FlaskTestCase(BaseTestCase):

    # Ensure that flask was set up correctly
    def test_index(self):
        response = self.client.get('/', content_type='html/text')
        self.assertEqual(200, response.status_code)

    def test_jar_appears_on_main_page(self):
        response = self.client.post('/', data=dict(currency='BTC'), follow_redirects=True)

        # Balance
        self.assertIn(b'0.0', response.data)
        # Currency
        self.assertIn(b'BTC', response.data)

    @mock.patch('application.Jar.transfer')
    def test_put_money_into_jar(self, mock_transfer):
        self.client.post('/jar/put/1', data=dict(amount='1', title='test_title'), follow_redirects=True)
        mock_transfer.assert_called_with(1, 'test_title')

    @mock.patch('application.Jar.transfer')
    def test_withdraw_from_jar(self, mock_transfer):
        jar = Jar.query.get(1)
        jar.balance_low_denom = 200
        db.session.add(jar)
        db.session.commit()

        self.client.post('/jar/withdraw/1', data=dict(amount='1', title='test_title'), follow_redirects=True)
        mock_transfer.assert_called_with(-1, 'test_title')

    def test_withdraw_from_empty_jar(self):
        jar = Jar.query.get(1)

        response = self.client.post('/jar/withdraw/1', data=dict(amount='1', title='test_title'), follow_redirects=True)
        self.assertIn(b'Illegal operation.', response.data)
        self.assertEqual(jar.balance, 0.0)

    def test_jar2jar(self):
        jar_charged = Jar(currency='BTC', balance_low_denom=1000)
        db.session.add(jar_charged)
        db.session.commit()
        jar_credited = Jar.query.get(1)
        test_title = 'test_title'
        jar_charged.transfer = mock.MagicMock()
        jar_credited.transfer = mock.MagicMock()

        self.client.post('/jar2jar/%s' % jar_charged.id,
                         data=dict(amount='1', title=test_title, jar_credited_id=jar_credited.id),
                         follow_redirects=True)

        jar_charged.transfer.assert_called_with(-1, test_title)
        jar_credited.transfer.assert_called_with(1, test_title)

    @mock.patch('application.Jar.transfer')
    def test_jar2jar_transfer_wrong_currency(self, mock_transfer):
        jar_charged = Jar(currency='Different Currency', balance_low_denom=1000)
        db.session.add(jar_charged)
        db.session.commit()
        jar_credited = Jar.query.get(1)

        # jar_credited should not be possible to choose
        response = self.client.get('/jar2jar/%s' % jar_charged.id)
        self.assertIn(b'Jar 2: 10.0 Different Currency', response.data)
        self.assertNotIn(b'Jar 1: 0.0 BTC', response.data)

        test_title = 'test_title'

        response = self.client.post('/jar2jar/%s' % jar_charged.id,
                         data=dict(amount='1', title=test_title, jar_credited_id=jar_credited.id),
                         follow_redirects=True)
        self.assertIn(b"Illegal operation", response.data)
        self.assertEqual(mock_transfer.call_count, 0)

    def test_transfer(self):
        jar = Jar.query.get(1)

        # There are no operations in /operations view at first
        response = self.client.get('/operations')
        self.assertIn(b'No operations yet!', response.data)

        jar.transfer(1, 'test_title')
        self.assertEqual(jar.balance, 1.0)

        # now, let's see if operation appeared in /operations view
        response = self.client.get('/operations')

        # Balance
        self.assertIn(b'1.0', response.data)
        # Currency
        self.assertIn(b'BTC', response.data)

        # now, let's see if operation appeared in jar's operations view
        response = self.client.get('/operations/1')

        # Balance
        self.assertIn(b'1.0', response.data)
        # Currency
        self.assertIn(b'BTC', response.data)


if __name__ == '__main__':
    unittest.main()
