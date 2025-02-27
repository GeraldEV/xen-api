"""Test module for dnf accesstoken, ptoken and xapitoken"""
import unittest
import sys
import json
from unittest.mock import MagicMock, patch
from python3.tests.import_helper import import_file_as_module

sys.modules["urlgrabber"] = MagicMock()

# Disable wrong import postition as need to mock some sys modules first
#pylint: disable=wrong-import-position

# Disable unused-argument as some mock obj is not used
#pylint: disable=unused-argument

# Some test case does not use self

accesstoken = import_file_as_module("python3/dnf_plugins/accesstoken.py")
ptoken = import_file_as_module("python3/dnf_plugins/ptoken.py")
xapitoken = import_file_as_module("python3/dnf_plugins/xapitoken.py")

REPO_NAME = "testrepo"


def _mock_repo(a_token=None, p_token=None, xapi_token=None, baseurl=None):
    mock_repo = MagicMock()
    mock_repo.accesstoken = a_token
    mock_repo.ptoken = p_token
    mock_repo.xapitoken = xapi_token
    mock_repo.baseurl = baseurl
    mock_base = MagicMock()
    mock_base.repos = {REPO_NAME: mock_repo}
    mock_repo.base = mock_base
    return mock_repo


@patch("accesstoken.urlgrabber")
class TestAccesstoken(unittest.TestCase):
    """Test class for dnf access plugin"""

    def test_set_http_header_with_access_token(self, mock_grabber):
        """test config succeed with accesstokan"""
        mock_repo = _mock_repo(a_token="file:///mock_accesstoken_url")
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "token": "valid_token",
            "token_id": "valid_token_id",
        })
        accesstoken.AccessToken(mock_repo.base, MagicMock()).config()
        mock_repo.set_http_headers.assert_called_with(
            ['X-Access-Token:valid_token','Referer:valid_token_id']
        )

    def test_repo_without_access_token(self, mock_grabber):
        """If repo has not accestoken, it should not be blocked"""
        mock_repo = _mock_repo()
        accesstoken.AccessToken(mock_repo.base, MagicMock()).config()
        mock_repo.set_http_headers.assert_not_called()

    def test_ignore_invalid_token_url(self, mock_grabber):
        """If repo provided an invalid token url, it should be ignored"""
        mock_repo = _mock_repo(a_token="Not_existed")
        mock_grabber.urlopen.side_effect = FileNotFoundError('')
        accesstoken.AccessToken(mock_repo.base, MagicMock()).config()
        assert not mock_repo.set_http_headers.called

    def test_invalid_token_raise_exception(self, mock_grabber):
        """Token with right json format, bad content should raise"""
        mock_repo = _mock_repo(a_token="file:///file_contain_invalid_token")
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "bad_token": "I am bad guy"
        })
        with self.assertRaises(accesstoken.InvalidToken):
            accesstoken.AccessToken(mock_repo.base, MagicMock()).config()


class TestPtoken(unittest.TestCase):
    """Test class for ptoken dnf plugin"""
    def test_failed_to_open_ptoken_file(self):
        """Exception should raised if the system does not have PTOKEN_PATH"""
        # Disable pyright warning as we need to set the PTOKEN_PATH to test the exception
        ptoken.PTOKEN_PATH = "/some/not/exist/path" # pyright: ignore[reportAttributeAccessIssue]
        with self.assertRaises(Exception):
            ptoken.Ptoken(MagicMock(), MagicMock()).config()

    @patch("builtins.open")
    def test_set_ptoken_to_http_header(self, mock_open):
        """Local repo with ptoken enabled should set the ptoken to its http header"""
        mock_open.return_value.__enter__.return_value.read.return_value = "valid_ptoken"
        mock_repo = _mock_repo(p_token=True, baseurl=["http://127.0.0.1/some_local_path"])
        ptoken.Ptoken(mock_repo.base, MagicMock()).config()
        mock_repo.set_http_headers.assert_called_with(["cookie:pool_secret=valid_ptoken"])

    @patch("builtins.open")
    def test_remote_repo_ignore_ptoken(self, mock_open):
        """non-local repo should just ignore the ptoken"""
        mock_open.return_value.__enter__.return_value.read.return_value = "valid_ptoken"
        mock_repo = _mock_repo(p_token=True, baseurl=["http://some_remote_token/some_local_path"])
        ptoken.Ptoken(mock_repo.base, MagicMock()).config()
        assert not  mock_repo.set_http_headers.called

    @patch("builtins.open")
    def test_local_repo_does_not_enable_ptoken_should_ignore_ptoken(self, mock_open):
        """local repo which has not enabled ptoken should just ignore the ptoken"""
        mock_open.return_value.__enter__.return_value.read.return_value = "valid_ptoken"
        mock_repo = _mock_repo(p_token=False, baseurl=["http://127.0.0.1/some_local_path"])
        ptoken.Ptoken(mock_repo.base, MagicMock()).config()
        assert not  mock_repo.set_http_headers.called

@patch("xapitoken.urlgrabber")
class TestXapitoken(unittest.TestCase):
    """Test class for xapitoken dnf plugin"""

    def test_set_http_header_with_xapi_token(self, mock_grabber):
        """test config succeed with xapitokan"""
        mock_repo = _mock_repo(xapi_token="file:///mock_xapitoken_url",
                               baseurl=["http://127.0.0.1/some_local_path"])
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "xapitoken": "valid_token",
        })
        xapitoken.XapiToken(mock_repo.base, MagicMock()).config()
        mock_repo.set_http_headers.assert_called_with(
            ['cookie:session_id=valid_token']
        )

    def test_repo_without_xapi_token(self, mock_grabber):
        """If repo has not xapitoken, it should not be blocked"""
        mock_repo = _mock_repo()
        xapitoken.XapiToken(mock_repo.base, MagicMock()).config()
        assert not mock_repo.set_http_headers.called

    def test_ignore_invalid_token_url(self, mock_grabber):
        """If repo provided an invalid token url, it should be ignored"""
        mock_repo = _mock_repo(xapi_token="Not_existed")
        xapitoken.XapiToken(mock_repo.base, MagicMock()).config()
        assert not mock_repo.set_http_headers.called

    def test_invalid_token_raise_exception(self, mock_grabber):
        """Token with right json format, bad content should raise"""
        mock_repo = _mock_repo(xapi_token="file:///file_contain_invalid_token",
                               baseurl=["http://127.0.0.1/some_local_path"])
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "bad_token": "I am bad guy"
        })
        with self.assertRaises(xapitoken.InvalidToken):
            xapitoken.XapiToken(mock_repo.base, MagicMock()).config()

    def test_remote_repo_ignore_xapitoken(self, mock_grabber):
        """non-local repo should just ignore the xapitoken"""
        mock_repo = _mock_repo(xapi_token=True,
                               baseurl=["http://some_remote_token/some_local_path"])
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "xapitoken": "valid_token",
        })
        xapitoken.XapiToken(mock_repo.base, MagicMock()).config()
        assert not mock_repo.set_http_headers.called

    def test_local_repo_does_not_enable_xapitoken_should_ignore_xapitoken(self, mock_grabber):
        """local repo which has not enabled xapitoken should just ignore the xapitoken"""
        mock_repo = _mock_repo(xapi_token=False, baseurl=["http://127.0.0.1/some_local_path"])
        mock_grabber.urlopen.return_value.read.return_value = json.dumps({
            "xapitoken": "valid_token",
        })
        xapitoken.XapiToken(mock_repo.base, MagicMock()).config()
        assert not mock_repo.set_http_headers.called
