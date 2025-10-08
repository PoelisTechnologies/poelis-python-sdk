"""Auth0 Client Credentials flow for SDK authentication.

This module handles automatic JWT token acquisition using Auth0 Client Credentials
flow when users provide API keys. The API key serves as the client_id, and we
derive the client_secret and audience from the API key format.
"""

from __future__ import annotations

import time
from typing import Optional

import httpx


class Auth0TokenManager:
    """Manages Auth0 JWT tokens using Client Credentials flow.
    
    Automatically acquires and refreshes tokens based on API keys.
    """
    
    def __init__(self, api_key: str, org_id: str, base_url: str) -> None:
        """Initialize token manager.
        
        Args:
            api_key: API key from webapp (used as client_id)
            org_id: Organization ID for audience
            base_url: Base URL to derive Auth0 domain and audience
        """
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = base_url
        
        # Extract Auth0 domain from API key format
        # Format: poelis_live_org_dev_<client_id>
        parts = api_key.split('_')
        if len(parts) >= 4 and parts[0] == 'poelis' and parts[1] == 'live' and parts[2] == 'org' and parts[3] == 'dev':
            # For now, use the Machine to Machine application credentials
            # TODO: Parse client_id from API key when webapp generates proper format
            self.client_id = "XcSLURURuQNEVvX2PF5DplNhTY6YCT4C"  # Machine to Machine app
            self.client_secret = "TM_Fv8FsfAaqvODf7ayyE_LrZM2KbbpdtLIIMqkIZwFXfKYLdOFcO2qmyO0v970-"
        else:
            raise ValueError("Invalid API key format. Expected: poelis_live_org_dev_<client_id>")
        
        # Derive Auth0 domain and audience
        self.auth0_domain = "poelis-prod.eu.auth0.com" 
        self.audience = "poelis-auth-api"  # Use the API identifier, not the GCP URL
        
        self._token: Optional[str] = None
        self._expires_at: float = 0
    
    def get_token(self) -> str:
        """Get valid JWT token, refreshing if needed.
        
        Returns:
            str: JWT token for Authorization header
        """
        if self._token and time.time() < self._expires_at - 60:  # Refresh 1min early
            return self._token
        
        return self._refresh_token()
    
    def _refresh_token(self) -> str:
        """Acquire new JWT token from Auth0.
        
        Returns:
            str: Fresh JWT token
        """
        token_url = f"https://{self.auth0_domain}/oauth/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials"
        }
        
        with httpx.Client() as client:
            response = client.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._expires_at = time.time() + expires_in
            
            return self._token
