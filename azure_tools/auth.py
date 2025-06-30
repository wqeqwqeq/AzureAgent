from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
from subprocess import PIPE, run


class AzureAuthentication:
    """
    Shared authentication class for Azure resources.
    Manages credentials and tokens only - no subscription management.
    """
    
    def __init__(self):
        """
        Initialize Azure authentication.
        """
        self.credential = DefaultAzureCredential()
        self.token = None
        self.token_expiry = None
    
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
            token_response = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            self.token = token_response.token
            # Convert expires_on (Unix timestamp) to datetime
            self.token_expiry = datetime.fromtimestamp(
                token_response.expires_on
            ) - timedelta(minutes=5)
        return self.token
