from typing import Callable, Optional
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential, DeviceCodeCredential,TokenCachePersistenceOptions
from azure.mgmt.resource import SubscriptionClient
from datetime import datetime, timedelta
import subprocess, re
from .config import settings 


class AzureAuthentication:
    """
    Shared authentication class for Azure resources.
    Manages credentials and tokens with support for multiple authentication methods.
    """
    
    def __init__(self,  device_code_callback : Optional[Callable] = None):
        """
        Initialize Azure authentication.
        
        Args:
            auth_method (str): Authentication method - "interactive", "device_code", or "default"
            tenant_id (str, optional): Azure tenant ID
            client_id (str, optional): Application client ID
        """
        self.auth_method = settings.azure_auth_method
        self.tenant_id = settings.azure_tenant_id
        self.client_id = settings.azure_client_id
        self.credential = None
        self.token = None
        self.token_expiry = None
        self.is_authenticated = False
        
        # Initialize credential based on method
        self._initialize_credential(device_code_callback)
    
    def _initialize_credential(self, device_code_callback : Optional[Callable] = None):
        """Initialize the credential object based on the authentication method."""
        if self.auth_method == "DEVICE_CODE":
            print("Device code authentication method selected")
            cache_opts = TokenCachePersistenceOptions(          # share across sessions
                            name="cli-like-cache",
                            allow_unencrypted_storage=True
            )   
              
            self.credential = DeviceCodeCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                prompt_callback=self._device_code_callback if device_code_callback is None else device_code_callback,
                cache_persistence_options=cache_opts
            )
            self._trigger_auth(self.credential)
        elif self.auth_method == "INTERACTIVE":
            print("Interactive authentication method selected")
            cache_opts = TokenCachePersistenceOptions(          # share across sessions
                            name="cli-like-cache",
                            allow_unencrypted_storage=True
            )   
            self.credential = InteractiveBrowserCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                cache_persistence_options=cache_opts
            )
            self._trigger_auth(self.credential)
        else:  # default
            self.credential = DefaultAzureCredential()
            self.is_authenticated = True
    

    def _trigger_auth(self,credential):
        sub = SubscriptionClient(credential)
        next(sub.subscriptions.list())
        print("Authentication successful")
        self.is_authenticated = True
            

    def _device_code_callback(self, verification_uri, user_code, expires_in):
        """
        Callback function for device code authentication.
        Prints the URL and code for user authentication.
        """
        print("\n" + "="*60)
        print("🔐 AZURE DEVICE CODE AUTHENTICATION")
        print("="*60)
        print(f"📱 Open this URL in your browser: {verification_uri}")
        print(f"🔑 Enter this code: {user_code}")
        print(f"⏰ This code expires in {expires_in} seconds")
        print("="*60)
        print("💡 You can use any device with a web browser to complete authentication")
        print("💡 After entering the code, you can close this terminal and continue on your device")
        print("="*60)

    def get_token(self):
        """
        Get a new token if current one is expired or doesn't exist.
        Returns cached token if still valid.
        """
        now = datetime.now()
        if (
            self.token is None
            or self.token_expiry is None
            or (self.token_expiry is not None and now >= self.token_expiry)
        ):
            print("Generating new token...")
            if self.auth_method == "device_code":
                print("📱 Device code authentication required...")
            
            token_response = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            self.token = token_response.token
            # Convert expires_on (Unix timestamp) to datetime
            self.token_expiry = datetime.fromtimestamp(
                token_response.expires_on
            ) - timedelta(minutes=5)
        return self.token




DEVICE_CODE_RE = re.compile(r"https://\S+"), re.compile(r"code\s+([A-Z0-9-]{8,})")

def start_az_login():
    """
    Launch 'az login --use-device-code' *once* and return
    (verification_uri, user_code, proc_handle).
    """
    check_auth = subprocess.Popen(
        ["az", "account", "show"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    check_auth.wait()
    if check_auth.poll() == 0:
        print("Azure account is already authenticated")
        return True, None, None, None

    proc = subprocess.Popen(
        ["az", "login", "--use-device-code", "--output", "none"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Read lines until we see the URI & code
    verification_uri, user_code = None, None
    for line in iter(proc.stdout.readline, ""):
        if "https://" in line and "code" in line:
            uri_m = re.search(r"https://\S+", line)
            code_m = re.search(r"code\s+([A-Z0-9-]{8,})", line)
            verification_uri = uri_m.group(0) if uri_m else "Link not found"
            user_code = code_m.group(1) if code_m else "Code not found"
            break          # we’ve got what we need – stop reading
    return False, verification_uri, user_code, proc

