import requests

class NPMClient:
    def __init__(self, base_url, verify_ssl=True, token=None, identity=None, secret=None):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = token
        self.identity = identity
        self.secret = secret

    def authenticate(self):
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return

        payload = {"identity": self.identity, "secret": self.secret}
        response = self.session.post(f"{self.base_url}/api/tokens", json=payload, timeout=30)
        response.raise_for_status()
        token = response.json()["token"]
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_proxy_hosts(self):
        response = self.session.get(f"{self.base_url}/api/nginx/proxy-hosts", timeout=30)
        response.raise_for_status()
        return response.json()

    def create_proxy_host(self, payload):
        response = self.session.post(f"{self.base_url}/api/nginx/proxy-hosts", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def update_proxy_host(self, host_id, payload):
        response = self.session.put(f"{self.base_url}/api/nginx/proxy-hosts/{host_id}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_access_lists(self):
        response = self.session.get(f"{self.base_url}/api/nginx/access-lists", timeout=30)
        response.raise_for_status()
        return response.json()

    def get_certificates(self):
        response = self.session.get(f"{self.base_url}/api/nginx/certificates", timeout=30)
        response.raise_for_status()
        return response.json()
