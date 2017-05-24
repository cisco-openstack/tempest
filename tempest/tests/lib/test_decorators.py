# Copyright 2013 IBM Corp
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import testtools

from tempest.lib import base as test
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.tests import base


class TestAttrDecorator(base.TestCase):
    def _test_attr_helper(self, expected_attrs, **decorator_args):
        @decorators.attr(**decorator_args)
        def foo():
            pass

        # By our decorators.attr decorator the attribute __testtools_attrs
        # will be set only for 'type' argument, so we test it first.
        if 'type' in decorator_args:
            # this is what testtools sets
            self.assertEqual(getattr(foo, '__testtools_attrs'),
                             set(expected_attrs))

    def test_attr_without_type(self):
        self._test_attr_helper(expected_attrs='baz', bar='baz')

    def test_attr_decorator_with_list_type(self):
        # if type is 'smoke' we'll get the original list of types
        self._test_attr_helper(expected_attrs=['smoke', 'foo'],
                               type=['smoke', 'foo'])

    def test_attr_decorator_with_unknown_type(self):
        self._test_attr_helper(expected_attrs=['foo'], type='foo')

    def test_attr_decorator_with_duplicated_type(self):
        self._test_attr_helper(expected_attrs=['foo'], type=['foo', 'foo'])


class TestSkipBecauseDecorator(base.TestCase):
    def _test_skip_because_helper(self, expected_to_skip=True,
                                  **decorator_args):
        class TestFoo(test.BaseTestCase):
            _interface = 'json'

            @decorators.skip_because(**decorator_args)
            def test_bar(self):
                return 0

        t = TestFoo('test_bar')
        if expected_to_skip:
            self.assertRaises(testtools.TestCase.skipException, t.test_bar)
        else:
            # assert that test_bar returned 0
            self.assertEqual(TestFoo('test_bar').test_bar(), 0)

    def test_skip_because_bug(self):
        self._test_skip_because_helper(bug='12345')

    def test_skip_because_bug_and_condition_true(self):
        self._test_skip_because_helper(bug='12348', condition=True)

    def test_skip_because_bug_and_condition_false(self):
        self._test_skip_because_helper(expected_to_skip=False,
                                       bug='12349', condition=False)

    def test_skip_because_bug_without_bug_never_skips(self):
        """Never skip without a bug parameter."""
        self._test_skip_because_helper(expected_to_skip=False,
                                       condition=True)
        self._test_skip_because_helper(expected_to_skip=False)

    def test_skip_because_invalid_bug_number(self):
        """Raise ValueError if with an invalid bug number"""
        self.assertRaises(ValueError, self._test_skip_because_helper,
                          bug='critical_bug')


class TestIdempotentIdDecorator(base.TestCase):
    def _test_helper(self, _id, **decorator_args):
        @decorators.idempotent_id(_id)
        def foo():
            """Docstring"""
            pass

        return foo

    def _test_helper_without_doc(self, _id, **decorator_args):
        @decorators.idempotent_id(_id)
        def foo():
            pass

        return foo

    def test_positive(self):
        _id = data_utils.rand_uuid()
        foo = self._test_helper(_id)
        self.assertIn('id-%s' % _id, getattr(foo, '__testtools_attrs'))
        self.assertTrue(foo.__doc__.startswith('Test idempotent id: %s' % _id))

    def test_positive_without_doc(self):
        _id = data_utils.rand_uuid()
        foo = self._test_helper_without_doc(_id)
        self.assertTrue(foo.__doc__.startswith('Test idempotent id: %s' % _id))

    def test_idempotent_id_not_str(self):
        _id = 42
        self.assertRaises(TypeError, self._test_helper, _id)

    def test_idempotent_id_not_valid_uuid(self):
        _id = '42'
        self.assertRaises(ValueError, self._test_helper, _id)


class TestSkipUnlessAttrDecorator(base.TestCase):
    def _test_skip_unless_attr(self, attr, expected_to_skip=True):
        class TestFoo(test.BaseTestCase):
            expected_attr = not expected_to_skip

            @decorators.skip_unless_attr(attr)
            def test_foo(self):
                pass

        t = TestFoo('test_foo')
        if expected_to_skip:
            self.assertRaises(testtools.TestCase.skipException,
                              t.test_foo)
        else:
            try:
                t.test_foo()
            except Exception:
                raise testtools.TestCase.failureException()

    def test_skip_attr_does_not_exist(self):
        self._test_skip_unless_attr('unexpected_attr')

    def test_skip_attr_false(self):
        self._test_skip_unless_attr('expected_attr')

    def test_no_skip_for_attr_exist_and_true(self):
        self._test_skip_unless_attr('expected_attr', expected_to_skip=False)


class TestRelatedBugDecorator(base.TestCase):
    def test_relatedbug_when_no_exception(self):
        f = mock.Mock()
        sentinel = object()

        @decorators.related_bug(bug="1234", status_code=500)
        def test_foo(self):
            f(self)

        test_foo(sentinel)
        f.assert_called_once_with(sentinel)

    def test_relatedbug_when_exception(self):
        class MyException(Exception):
            def __init__(self, status_code):
                self.status_code = status_code

        def f(self):
            raise MyException(status_code=500)

        @decorators.related_bug(bug="1234", status_code=500)
        def test_foo(self):
            f(self)

        with mock.patch.object(decorators.LOG, 'error') as m_error:
            self.assertRaises(MyException, test_foo, object())

        m_error.assert_called_once_with(mock.ANY, '1234', '1234')
