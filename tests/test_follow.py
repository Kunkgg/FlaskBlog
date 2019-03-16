import unittest

from app.models import User, Follow
from app import db


class FollowTestCase(unittest.TestCase):
    def test_follow_unfollow(self):
        user1 = User(username='test1', email='test1@example.com', password='1')
        user2 = User(username='test2', email='test2@example.com', password='1')
        user1.follow(user2)
        db.session.commit()
        self.assertTrue(user1.is_following(user2))
        user1.unfollow(user2)
        db.session.commit()
        self.assertFalse(user1.is_following(user2))

    def test_is_followed_by(self):
        user3 = User(username='test3', email='test3@example.com', password='1')
        user4 = User(username='test4', email='test4@example.com', password='1')
        user3.follow(user4)
        db.session.commit()
        self.assertTrue(user4.is_followed_by(user3))

    def test_is_following(self):
        user5 = User(username='test5', email='test5@example.com', password='1')
        user6 = User(username='test6', email='test6@example.com', password='1')
        user5.follow(user6)
        db.session.commit()
        f = Follow.query.filter_by(follower_id=user5.id).first()
        if f.follower_id == user5.id and f.followed_id == user6.id:
            self.assertTrue(user5.is_following(user6))