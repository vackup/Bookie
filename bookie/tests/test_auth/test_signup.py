"""Test the limited signup process

"""
import logging

from nose.tools import eq_
from nose.tools import ok_

from bookie.models import DBSession
from bookie.models.auth import Activation
from bookie.models.auth import User
from bookie.models.auth import UserMgr

from bookie.tests import gen_random_word
from bookie.tests import TestDBBase
from bookie.tests import TestViewBase

LOG = logging.getLogger(__name__)


class TestInviteSetup(TestDBBase):
    """Verify we have/can work with the invite numbers"""

    def testHasNoInvites(self):
        """Verify that if the user has no invites, they can't invite"""
        u = User()
        u.invite_ct = 0
        ok_(not u.has_invites(), 'User should have no invites')
        ok_(not u.invite('me@you.com'), 'Should not be able to invite a user')

    def testInviteCreatesUser(self):
        """We should get a new user when inviting something"""
        me = User()
        me.username = 'me'
        me.email = 'me.com'
        me.invite_ct = 2
        you = me.invite('you.com')

        eq_('you.com', you.username,
            'The email should be the username')
        eq_('you.com', you.email,
            'The email should be the email')
        ok_(len(you.api_key),
            'The api key should be generated for the user')
        ok_(not you.activated,
            'The new user should not be activated')
        eq_(1, me.invite_ct,
            'My invite count should be deprecated')


class TestSigningUpUser(TestDBBase):
    """Start out by verifying a user starts out in the right state"""

    def testInitialUserInactivated(self):
        """A new user signup should be a deactivated user"""
        u = User()
        u.email = gen_random_word(10)
        DBSession.add(u)

        eq_(False, u.activated,
            'A new signup should start out deactivated by default')
        ok_(u.activation.code is not None,
            'A new signup should start out as deactivated')
        eq_('signup', u.activation.created_by,
            'This is a new signup, so mark is as thus')


class TestOpenSignup(TestViewBase):
    """New users can request a signup for an account."""

    def tearDown(self):
        super(TestOpenSignup, self).tearDown()
        User.query.filter(User.email == 'testing@newuser.com').delete()

    def testSignupRenders(self):
        """A signup form is kind of required."""
        res = self.app.get('/signup')

        self.assertIn('Sign up for Bookie', res.body)
        self.assertNotIn('class="error"', res.body)

    def testEmailRequired(self):
        """Signup requires an email entry."""
        res = self.app.post('/signup_process')
        self.assertIn('Please supply', res.body)

    def testEmailNotAlreadyThere(self):
        """Signup requires an email entry."""
        res = self.app.post(
            '/signup_process',
            params={
                'email': 'testing@dummy.com'
            }
        )
        self.assertIn('already signed up', res.body)

    def testSignupWorks(self):
        """Signing up stores an activation."""
        email = 'testing@newuser.com'
        UserMgr.signup_user(email, 'testcase')

        activations = Activation.query.all()

        self.assertTrue(len(activations) == 1)
        act = activations[0]

        self.assertEqual(
            email,
            act.user.email,
            "The activation email is the correct one.")
