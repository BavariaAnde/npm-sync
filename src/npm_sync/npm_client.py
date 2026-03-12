import requests

DEFAULT_TIMEOUT = 30


class NPMClient:
    def __init__(self, base_url, verify_ssl=True, token=None, identity=None, secret=None, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = token
        self.identity = identity
        self.secret = secret
        self.timeout = timeout

    def _auth_header_value(self) -> str | None:
        if not self.token:
            return None
        token = str(self.token).strip()
        if not token:
            return None
        if token.lower().startswith("bearer "):
            return token
        return f"Bearer {token}"

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            message = f"{response.status_code} {response.text}"
            raise requests.HTTPError(message, response=response)

    def authenticate(self):
        if self.token:
            auth_value = self._auth_header_value()
            if auth_value:
                self.session.headers.update({"Authorization": auth_value})
                return

        if not self.identity or not self.secret:
            raise ValueError("NPM_IDENTITY and NPM_SECRET are required when NPM_TOKEN is not set")

        payload = {"identity": self.identity, "secret": self.secret}
        response = self.session.post(f"{self.base_url}/api/tokens", json=payload, timeout=self.timeout)
        self._raise_for_status(response)
        token = response.json()["token"]
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_proxy_hosts(self):
        response = self.session.get(f"{self.base_url}/api/nginx/proxy-hosts", timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()

    def create_proxy_host(self, payload):
        response = self.session.post(f"{self.base_url}/api/nginx/proxy-hosts", json=payload, timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()

    def update_proxy_host(self, host_id, payload):
        response = self.session.put(
            f"{self.base_url}/api/nginx/proxy-hosts/{host_id}", json=payload, timeout=self.timeout
        )
        self._raise_for_status(response)
        return response.json()

    def delete_proxy_host(self, host_id):
        response = self.session.delete(f"{self.base_url}/api/nginx/proxy-hosts/{host_id}", timeout=self.timeout)
        self._raise_for_status(response)
        return True

    def get_access_lists(self):
        response = self.session.get(f"{self.base_url}/api/nginx/access-lists", timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()

    def get_certificates(self):
        response = self.session.get(f"{self.base_url}/api/nginx/certificates", timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()

    def create_certificate(self, payload):
        response = self.session.post(f"{self.base_url}/api/nginx/certificates", json=payload, timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()
