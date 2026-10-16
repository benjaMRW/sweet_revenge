import sqlite3
import unittest

import app as clock_app


class AdminLocationTests(unittest.TestCase):
    def setUp(self):
        self.client = clock_app.app.test_client()
        with sqlite3.connect(clock_app.DB_NAME) as conn:
            conn.execute('DELETE FROM attendance')
            conn.execute(
                'INSERT INTO attendance (name, action, location, timestamp) VALUES (?, ?, ?, ?)',
                ('Alex', 'Clock In', 'Kitchen', '2024-01-01 09:00:00')
            )
            conn.execute(
                'INSERT INTO attendance (name, action, location, timestamp) VALUES (?, ?, ?, ?)',
                ('Alex', 'Clock Out', 'Kitchen', '2024-01-01 17:00:00')
            )
            conn.execute(
                'INSERT INTO attendance (name, action, location, timestamp) VALUES (?, ?, ?, ?)',
                ('Alex', 'Clock In', 'Market', '2024-01-01 10:00:00')
            )
            conn.execute(
                'INSERT INTO attendance (name, action, location, timestamp) VALUES (?, ?, ?, ?)',
                ('Alex', 'Clock Out', 'Market', '2024-01-01 18:00:00')
            )
            conn.commit()

    def test_same_day_same_name_keeps_both_locations(self):
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True

        response = self.client.get('/admin')
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Kitchen', text)
        self.assertIn('Market', text)
        self.assertGreater(text.count('Alex'), 1)


if __name__ == '__main__':
    unittest.main()
