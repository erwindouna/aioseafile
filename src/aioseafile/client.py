"""Base client for the Seafile Web API."""

import socket
from contextlib import asynccontextmanager
from importlib import metadata
from typing import TYPE_CHECKING, Any, Self

from aiohttp import ClientError, ClientResponse, ClientResponseError, ClientSession, ClientTimeout
from aiohttp.hdrs import METH_GET, METH_POST
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential
from yarl import URL

from aioseafile.exceptions import (
    SeafileAuthenticationError,
    SeafileConnectionError,
    SeafileError,
    SeafileNotFoundError,
    SeafilePermissionError,
    SeafileTimeoutError,
    SeafileTwoFactorRequiredError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

try:
    VERSION = metadata.version(__package__)
except metadata.PackageNotFoundError:  # pragma: no cover
    VERSION = "DEV-0.0.0"  # pylint: disable=invalid-name

FILE_SERVER_PREFIX = "/seafhttp/"


def _is_retryable(err: BaseException) -> bool:
    """Return whether a failed request is worth retrying.

    Client errors (4xx) won't succeed on a retry, except request timeouts (408)
    and rate limits (429).
    """
    if not isinstance(err, (SeafileConnectionError, SeafileTimeoutError)):
        return False
    cause = err.__cause__
    return not (isinstance(cause, ClientResponseError) and 400 <= cause.status < 500 and cause.status not in (408, 429))


def _raise_for_status(method: str, url: URL, status: int, body: str, err: ClientResponseError) -> None:
    """Map an error response to a Seafile exception."""
    match status:
        case 401:
            msg = f"Authentication failed for {method} {url}: {body}"
            raise SeafileAuthenticationError(msg) from err
        case 403:
            msg = f"Permission denied for {method} {url}: {body}"
            raise SeafilePermissionError(msg) from err
        case 404:
            msg = f"Resource not found at {method} {url}: {body}"
            raise SeafileNotFoundError(msg) from err
        case _:
            msg = f"Error {status} for {method} {url}: {body}"
            raise SeafileConnectionError(msg) from err


class SeafileClient:
    """Connection handling shared by all Seafile API groups."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        api_url: str,
        token: str | None = None,
        *,
        request_timeout: float = 10.0,
        transfer_timeout: float = 300.0,
        session: ClientSession | None = None,
        max_retries: int = 3,
        file_server_url: str | None = None,
    ) -> None:
        """Initialize the Seafile object.

        Args:
        ----
            api_url: Base URL of the Seafile server, for example 'https://cloud.example.com'.
            token: Account token; obtain one with `get_auth_token` if omitted.
            request_timeout: Timeout for API requests (in seconds).
            transfer_timeout: Maximum time without data during an upload or download (in seconds).
            session: Optional aiohttp session to use.
            max_retries: Maximum number of retry attempts on transient errors.
            file_server_url: Base URL of the file server. Seafile builds upload and
                download links from its own SERVICE_URL setting, which often differs
                from the address this client uses; links are rebased onto this URL.
                Defaults to `<api_url>/seafhttp/`.

        """
        self._url = URL(api_url.rstrip("/") + "/")
        self._file_server_url = URL(file_server_url.rstrip("/") + "/") if file_server_url else self._url.join(URL("seafhttp/"))
        self._token = token
        self._request_timeout = request_timeout
        self._transfer_timeout = transfer_timeout
        self._session = session
        self._close_session = False
        self._max_retries = max_retries

    def _get_session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession()
            self._close_session = True
        return self._session

    def _headers(self, *, authenticated: bool, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": f"PythonSeafile/{VERSION}", **(extra or {})}
        if authenticated:
            if self._token is None:
                msg = "No token set; call get_auth_token first"
                raise SeafileAuthenticationError(msg)
            headers["Authorization"] = f"Token {self._token}"
        return headers

    def file_server_link(self, link: str) -> URL:
        """Rebase an upload or download link from Seafile onto the file server URL."""
        url = URL(link)
        if not url.path.startswith(FILE_SERVER_PREFIX):
            return url
        return self._file_server_url.join(URL(url.raw_path.removeprefix(FILE_SERVER_PREFIX))).with_query(url.raw_query_string)

    async def _request(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        uri: str | URL,
        *,
        method: str = METH_GET,
        params: dict[str, Any] | None = None,
        data: Any = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        authenticated: bool = True,
        client_timeout: ClientTimeout | None = None,
        retry: bool = True,
        text: bool = False,
    ) -> Any:
        """Handle a request to the Seafile Web API.

        Args:
        ----
            uri: Request URI relative to the server root, for example 'api2/ping/', or an absolute URL.
            method: HTTP method to use.
            params: Query parameters.
            data: Form data or payload to send.
            json_body: JSON body to send.
            headers: Extra headers.
            authenticated: Whether to send the account token.
            client_timeout: Timeout for the request; defaults to `request_timeout` in total.
            retry: Whether transient errors may be retried; disable for one-shot payloads.
            text: Return the body as text instead of decoding JSON.

        Returns:
        -------
            The JSON decoded response, or None for an empty response.

        """
        url = uri if isinstance(uri, URL) else self._url.join(URL(uri))
        request_headers = self._headers(authenticated=authenticated, extra=headers)
        session = self._get_session()
        client_timeout = client_timeout or ClientTimeout(total=self._request_timeout)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(self._max_retries + 1 if retry else 1),
            reraise=True,
        ):
            with attempt:
                body = ""
                try:
                    response = await session.request(
                        method,
                        url,
                        headers=request_headers,
                        params=params,
                        data=data,
                        json=json_body,
                        timeout=client_timeout,
                    )
                    body = await response.text()
                    response.raise_for_status()
                except TimeoutError as err:
                    msg = f"Timeout error while accessing {method} {url}"
                    raise SeafileTimeoutError(msg) from err
                except ClientResponseError as err:
                    _raise_for_status(method, url, err.status, body, err)
                except (ClientError, socket.gaierror) as err:
                    msg = f"Unexpected error during {method} {url}: {err}"
                    raise SeafileConnectionError(msg) from err

        if text:
            return body
        if not body:
            return None
        try:
            return await response.json(content_type=None)
        except ValueError as err:
            msg = "Unexpected response from the Seafile API"
            raise SeafileError(msg, {"Content-Type": response.headers.get("Content-Type", ""), "response": body}) from err

    @asynccontextmanager
    async def _stream(self, url: URL) -> AsyncIterator[ClientResponse]:
        """Open a streaming GET request, for example a file download."""
        session = self._get_session()
        timeout = ClientTimeout(total=None, connect=self._request_timeout, sock_read=self._transfer_timeout)
        try:
            response = await session.get(url, headers=self._headers(authenticated=False), timeout=timeout)
        except TimeoutError as err:
            msg = f"Timeout error while accessing GET {url}"
            raise SeafileTimeoutError(msg) from err
        except (ClientError, socket.gaierror) as err:
            msg = f"Unexpected error during GET {url}: {err}"
            raise SeafileConnectionError(msg) from err
        try:
            if response.status >= 400:
                body = await response.text()
                error = ClientResponseError(response.request_info, response.history, status=response.status)
                _raise_for_status("GET", url, response.status, body, error)
            yield response
        finally:
            response.release()

    async def get_auth_token(  # pylint: disable=too-many-arguments
        self,
        username: str,
        password: str,
        otp: str | None = None,
        *,
        device_id: str | None = None,
        device_name: str | None = None,
        platform: str = "linux",
    ) -> str:
        """Exchange credentials for an account token and use it for later requests.

        Args:
        ----
            username: Account email or login ID.
            password: Account password.
            otp: Two-factor authentication code, if the account requires one.
            device_id: Register the token as a device (40 characters for desktop
                platforms), so the user can see and revoke it in Seafile.
            device_name: Name of the device shown in Seafile.
            platform: Device platform, used with `device_id`.

        Returns:
        -------
            The account token.

        Raises:
        ------
            SeafileTwoFactorRequiredError: The account requires an `otp` code.
            SeafileAuthenticationError: The credentials are invalid.

        """
        url = self._url.join(URL("api2/auth-token/"))
        headers = self._headers(authenticated=False)
        if otp is not None:
            headers["X-SEAFILE-OTP"] = otp
        form = {"username": username, "password": password}
        if device_id is not None:
            form |= {"device_id": device_id, "device_name": device_name or device_id, "platform": platform, "client_version": VERSION}

        try:
            response = await self._get_session().post(url, headers=headers, data=form, timeout=ClientTimeout(total=self._request_timeout))
            result = await response.json(content_type=None)
        except TimeoutError as err:
            msg = f"Timeout error while accessing {METH_POST} {url}"
            raise SeafileTimeoutError(msg) from err
        except (ClientError, socket.gaierror, ValueError) as err:
            msg = f"Unexpected error during {METH_POST} {url}: {err}"
            raise SeafileConnectionError(msg) from err

        if response.status == 400:
            if response.headers.get("X-Seafile-OTP") == "required":
                msg = "Two-factor authentication code required"
                raise SeafileTwoFactorRequiredError(msg)
            msg = f"Authentication failed: {result}"
            raise SeafileAuthenticationError(msg)
        if response.status != 200:
            msg = f"Error {response.status} for {METH_POST} {url}: {result}"
            raise SeafileConnectionError(msg)

        self._token = result["token"]
        return self._token

    async def close(self) -> None:
        """Close open client session."""
        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The Seafile object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
