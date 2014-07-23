            #    Copyright (C) 2013 Hewlett-Packard Development Company, L.P.
#
#    Author: Juerg Haefliger <juerg.haefliger@hp.com>
#
#    Based on test_handler_set_hostname.py
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from cloudinit.config import cc_seed_random

import base64
import gzip
import tempfile

from StringIO import StringIO

from cloudinit import cloud
from cloudinit import distros
from cloudinit import helpers
from cloudinit import util

from cloudinit.sources import DataSourceNone

from .. import helpers as t_help

import logging

LOG = logging.getLogger(__name__)


class TestRandomSeed(t_help.TestCase):
    def setUp(self):
        super(TestRandomSeed, self).setUp()
        self._seed_file = tempfile.mktemp()
        self.unapply = []

        # by default 'which' has nothing in its path
        self.apply_patches([(util, 'which', self._which)])
        self.apply_patches([(util, 'subp', self._subp)])
        self.subp_called = []
        self.whichdata = {}

    def tearDown(self):
        apply_patches([i for i in reversed(self.unapply)])
        util.del_file(self._seed_file)

    def apply_patches(self, patches):
        ret = apply_patches(patches)
        self.unapply += ret

    def _which(self, program):
        return self.whichdata.get(program)

    def _subp(self, *args, **kwargs):
        # supports subp calling with cmd as args or kwargs
        if 'args' not in kwargs:
            kwargs['args'] = args[0]
        self.subp_called.append(kwargs)
        return

    def _compress(self, text):
        contents = StringIO()
        gz_fh = gzip.GzipFile(mode='wb', fileobj=contents)
        gz_fh.write(text)
        gz_fh.close()
        return contents.getvalue()

    def _get_cloud(self, distro, metadata=None):
        paths = helpers.Paths({})
        cls = distros.fetch(distro)
        ubuntu_distro = cls(distro, {}, paths)
        ds = DataSourceNone.DataSourceNone({}, ubuntu_distro, paths)
        if metadata:
            ds.metadata = metadata
        return cloud.Cloud(ds, paths, {}, ubuntu_distro, None)

    def test_append_random(self):
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': 'tiny-tim-was-here',
            }
        }
        cc_seed_random.handle('test', cfg, self._get_cloud('ubuntu'), LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals("tiny-tim-was-here", contents)

    def test_append_random_unknown_encoding(self):
        data = self._compress("tiny-toe")
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': data,
                'encoding': 'special_encoding',
            }
        }
        self.assertRaises(IOError, cc_seed_random.handle, 'test', cfg,
                          self._get_cloud('ubuntu'), LOG, [])

    def test_append_random_gzip(self):
        data = self._compress("tiny-toe")
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': data,
                'encoding': 'gzip',
            }
        }
        cc_seed_random.handle('test', cfg, self._get_cloud('ubuntu'), LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals("tiny-toe", contents)

    def test_append_random_gz(self):
        data = self._compress("big-toe")
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': data,
                'encoding': 'gz',
            }
        }
        cc_seed_random.handle('test', cfg, self._get_cloud('ubuntu'), LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals("big-toe", contents)

    def test_append_random_base64(self):
        data = base64.b64encode('bubbles')
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': data,
                'encoding': 'base64',
            }
        }
        cc_seed_random.handle('test', cfg, self._get_cloud('ubuntu'), LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals("bubbles", contents)

    def test_append_random_b64(self):
        data = base64.b64encode('kit-kat')
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': data,
                'encoding': 'b64',
            }
        }
        cc_seed_random.handle('test', cfg, self._get_cloud('ubuntu'), LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals("kit-kat", contents)

    def test_append_random_metadata(self):
        cfg = {
            'random_seed': {
                'file': self._seed_file,
                'data': 'tiny-tim-was-here',
            }
        }
        c = self._get_cloud('ubuntu', {'random_seed': '-so-was-josh'})
        cc_seed_random.handle('test', cfg, c, LOG, [])
        contents = util.load_file(self._seed_file)
        self.assertEquals('tiny-tim-was-here-so-was-josh', contents)

    def test_seed_command_not_provided_pollinate_available(self):
        c = self._get_cloud('ubuntu', {})
        self.whichdata = {'pollinate': '/usr/bin/pollinate'}
        cc_seed_random.handle('test', {}, c, LOG, [])

        subp_args = [f['args'] for f in self.subp_called]
        self.assertIn(['pollinate', '-q'], subp_args)

    def test_seed_command_not_provided_pollinate_not_available(self):
        c = self._get_cloud('ubuntu', {})
        self.whichdata = {}
        cc_seed_random.handle('test', {}, c, LOG, [])

        # subp should not have been called as which would say not available
        self.assertEquals(self.subp_called, list())

    def test_unavailable_seed_command_and_required_raises_error(self):
        c = self._get_cloud('ubuntu', {})
        self.whichdata = {}
        self.assertRaises(ValueError, cc_seed_random.handle,
            'test', {'random_seed': {'command_required': True}}, c, LOG, [])

    def test_seed_command_and_required(self):
        c = self._get_cloud('ubuntu', {})
        self.whichdata = {'foo': 'foo'}
        cfg = {'random_seed': {'command_required': True, 'command': ['foo']}}
        cc_seed_random.handle('test', cfg, c, LOG, [])

        self.assertIn(['foo'], [f['args'] for f in self.subp_called])

    def test_file_in_environment_for_command(self):
        c = self._get_cloud('ubuntu', {})
        self.whichdata = {'foo': 'foo'}
        cfg = {'random_seed': {'command_required': True, 'command': ['foo'],
                               'file': self._seed_file}}
        cc_seed_random.handle('test', cfg, c, LOG, [])

        # this just instists that the first time subp was called,
        # RANDOM_SEED_FILE was in the environment set up correctly
        subp_env = [f['env'] for f in self.subp_called]
        self.assertEqual(subp_env[0].get('RANDOM_SEED_FILE'), self._seed_file)


def apply_patches(patches):
    ret = []
    for (ref, name, replace) in patches:
        if replace is None:
            continue
        orig = getattr(ref, name)
        setattr(ref, name, replace)
        ret.append((ref, name, orig))
    return ret
