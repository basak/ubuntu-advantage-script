"""Tests for ESM-related commands."""

from testing import UbuntuAdvantageTest
from fakes import APT_GET_LOG_WRAPPER


class ESMTest(UbuntuAdvantageTest):

    SERIES = 'precise'

    def setUp(self):
        super().setUp()
        self.setup_esm()

    def test_enable_esm(self):
        """The enable-esm option enables the ESM repository."""
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)
        expected = (
            'deb https://esm.ubuntu.com/ubuntu precise main\n'
            '# deb-src https://esm.ubuntu.com/ubuntu precise main\n')
        self.assertEqual(expected, self.esm_repo_list.read_text())
        self.assertEqual(
            self.apt_auth_file.read_text(),
            'machine esm.ubuntu.com/ubuntu/ login user password pass\n')
        self.assertEqual(self.apt_auth_file.stat().st_mode, 0o100600)
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_esm_enabled(self):
        """The enable-esm command fails if ESM is already enabled."""
        self.setup_esm(enabled=True)
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is already enabled',
            process.stderr)

    def test_enable_esm_any_arch(self):
        """ESM can be enabled on any arch."""
        self.arch = 'random-arch'
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)

    def test_enable_esm_auth_with_other_entries(self):
        """Existing auth.conf entries are preserved."""
        auth = 'machine example.com login user password pass\n'
        self.apt_auth_file.write_text(auth)
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(auth, self.apt_auth_file.read_text())

    def test_enable_esm_install_apt_transport_https(self):
        """enable-esm installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_esm_install_apt_transport_https_apt_get_options(self):
        """apt-get accepts defaults when installing apt-transports-https."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command=APT_GET_LOG_WRAPPER)
        self.script('enable-esm', 'user:pass')
        # apt-get is called both to install packages and update lists
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold install '
            'apt-transport-https',
            self.read_file('apt_get.args'))
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold update',
            self.read_file('apt_get.args'))
        self.assertIn(
            'DEBIAN_FRONTEND=noninteractive', self.read_file('apt_get.env'))

    def test_enable_esm_invalid_token(self):
        """If token is invalid, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  401  Unauthorized [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn('Invalid token', process.stderr)

    def test_enable_esm_invalid_token_trusty(self):
        """Invalid token error is caught with apt-helper in trusty."""
        message = 'E: Failed to fetch https://esm.ubuntu.com/  HttpError401'
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn('Invalid token', process.stderr)

    def test_enable_esm_error_checking_token(self):
        """If token check fails, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  404  Not Found [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn(
            'Failed checking token (404  Not Found [IP: 1.2.3.4])',
            process.stderr)

    def test_enable_esm_skip_token_check_no_helper(self):
        """If apt-helper is not found, the token check is skipped."""
        self.apt_helper.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Checking token... SKIPPED', process.stdout)

    def test_enable_esm_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_install_ca_certificates(self):
        """enable-esm installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_esm_install_ca_certificates_apt_get_options(self):
        """apt-get accepts defaults when installing ca-certificates."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command=APT_GET_LOG_WRAPPER)
        self.script('enable-esm', 'user:pass')
        # apt-get is called both to install packages and update lists
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold install ca-certificates',
            self.read_file('apt_get.args'))
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold update',
            self.read_file('apt_get.args'))
        self.assertIn(
            'DEBIAN_FRONTEND=noninteractive', self.read_file('apt_get.env'))

    def test_enable_esm_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_missing_token(self):
        """The token must be specified when using enable-esm."""
        process = self.script('enable-esm')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_invalid_token_format(self):
        """The ESM token must be specified as "user:password"."""
        process = self.script('enable-esm', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_only_supported_on_precise(self):
        """The enable-esm option fails if not on Precise."""
        self.SERIES = 'xenial'
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not supported on xenial',
            process.stderr)

    def test_disable_esm(self):
        """The disable-esm option disables the ESM repository."""
        other_auth = 'machine example.com login user password pass\n'
        self.apt_auth_file.write_text(other_auth)
        self.script('enable-esm', 'user:pass')
        self.setup_esm(enabled=True)
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository disabled', process.stdout)
        self.assertFalse(self.esm_repo_list.exists())
        # the keyring file is removed
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertFalse(keyring_file.exists())
        # credentials are removed
        self.assertEqual(self.apt_auth_file.read_text(), other_auth)

    def test_disable_esm_fails_already_disabled(self):
        """If the ESM repo is not enabled, disable-esm returns an error."""
        process = self.script('disable-esm')
        self.assertEqual(8, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not enabled', process.stderr)

    def test_disable_esm_only_supported_on_precise(self):
        """The disable-esm option fails if not on Precise."""
        self.SERIES = 'xenial'
        process = self.script('disable-esm')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not supported on xenial',
            process.stderr)

    def test_is_esm_enabled_true(self):
        """is-esm-enabled returns 0 if the repository is enabled."""
        self.setup_esm(enabled=True)
        process = self.script('is-esm-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_esm_enabled_false(self):
        """is-esm-enabled returns 1 if the repository is not enabled."""
        process = self.script('is-esm-enabled')
        self.assertEqual(1, process.returncode)
