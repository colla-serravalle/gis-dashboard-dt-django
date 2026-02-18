"""
ArcGIS Service for querying feature layers and managing tokens.

Ported from PHP ArcGISService.php
"""

import time
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache key for ArcGIS token
ARCGIS_TOKEN_CACHE_KEY = 'arcgis_token'


class ArcGISService:
    """Service class for interacting with ArcGIS REST API."""

    def __init__(self):
        self.portal_url = settings.ARCGIS_PORTAL_URL
        self.feature_service_url = settings.ARCGIS_FEATURE_SERVICE_URL
        self.username = settings.ARCGIS_USERNAME
        self.password = settings.ARCGIS_PASSWORD
        self.referer = settings.ARCGIS_REFERER
        self.token_expiration_minutes = settings.ARCGIS_TOKEN_EXPIRATION_MINUTES
        self.headers = {'Referer': self.referer}

    def get_token(self) -> str:
        """
        Get ArcGIS token, using cache if available and valid.

        Returns:
            str: Valid ArcGIS authentication token

        Raises:
            ArcGISError: If token generation fails
        """
        # Check cache first
        cached_token = cache.get(ARCGIS_TOKEN_CACHE_KEY)
        if cached_token:
            logger.debug("ArcGIS token found in cache")
            return cached_token

        # Generate new token
        logger.info(f"Requesting new ArcGIS token from {self.portal_url} for user {self.username}")
        params = {
            'username': self.username,
            'password': self.password,
            'client': 'referer',
            'referer': self.referer,
            'expiration': self.token_expiration_minutes,
            'f': 'json'
        }

        try:
            logger.debug(f"Sending token request with expiration: {self.token_expiration_minutes} minutes")
            response = requests.post(
                self.portal_url,
                data=params,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if 'token' not in data:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"ArcGIS token generation failed: {error_msg}")
                raise ArcGISError(f"Token generation failed: {error_msg}")

            token = data['token']
            logger.info(f"Successfully obtained ArcGIS token (expires in {self.token_expiration_minutes} minutes)")

            # Cache the token (expire 1 minute before actual expiration)
            cache_timeout = (self.token_expiration_minutes * 60) - 60
            cache.set(ARCGIS_TOKEN_CACHE_KEY, token, cache_timeout)
            logger.debug(f"Token cached for {cache_timeout} seconds")

            return token

        except requests.RequestException as e:
            logger.error(f"ArcGIS token request failed: {str(e)}", exc_info=True)
            raise ArcGISError(f"Connection error: {e}") from e

    def query_layer(self, layer_id: int, where: str = "1=1", out_fields: str = "*") -> dict:
        """
        Query a feature layer.

        Args:
            layer_id: The layer index in the feature service
            where: SQL WHERE clause for filtering
            out_fields: Fields to return (default: all)

        Returns:
            dict: Query results with 'features' list
        """
        logger.info(f"Querying ArcGIS layer {layer_id} with WHERE clause: {where}")
        logger.debug(f"Output fields: {out_fields}")
        
        token = self.get_token()

        params = {
            'where': where,
            'outFields': out_fields,
            'f': 'json',
            'token': token
        }

        url = f"{self.feature_service_url}/{layer_id}/query"
        logger.debug(f"Query URL: {url}")

        try:
            logger.debug("Sending query request to ArcGIS")
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

            logger.debug(f"Response status code: {response.status_code}, Full response keys: {list(result.keys())}")

            if 'error' in result and 'features' not in result:
                error_msg = result['error'].get('message', str(result['error']))
                logger.error(f"ArcGIS query returned an error for layer {layer_id}: {error_msg}")
                return {'error': error_msg}

            features_count = len(result.get('features', []))
            logger.info(f"Successfully queried layer {layer_id}, returned {features_count} features")

            return result

        except requests.RequestException as e:
            logger.error(f"ArcGIS query failed for layer {layer_id}: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def get_attachments(self, layer_id: int, object_id: int) -> dict:
        """
        Get attachments for a feature.

        Args:
            layer_id: The layer index
            object_id: The feature's OBJECTID

        Returns:
            dict: Attachment info with 'attachmentInfos' list
        """
        logger.info(f"Fetching attachments for layer {layer_id}, object ID {object_id}")
        
        token = self.get_token()

        url = f"{self.feature_service_url}/{layer_id}/{object_id}/attachments"
        params = {
            'f': 'json',
            'token': token
        }
        logger.debug(f"Attachments URL: {url}")

        try:
            logger.debug("Sending attachments request to ArcGIS")
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            
            attachments_count = len(result.get('attachmentInfos', []))
            logger.info(f"Successfully retrieved {attachments_count} attachments for layer {layer_id}, object ID {object_id}")
            logger.debug(f"Response status code: {response.status_code}")
            
            return result

        except requests.RequestException as e:
            logger.error(f"ArcGIS attachments request failed for layer {layer_id}, object ID {object_id}: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def get_attachment_content(self, layer_id: int, object_id: int, attachment_id: int) -> tuple:
        """
        Get the binary content of an attachment.

        Args:
            layer_id: The layer index
            object_id: The feature's OBJECTID
            attachment_id: The attachment ID

        Returns:
            tuple: (content_bytes, content_type) or (None, None) on error
        """
        logger.info(f"Downloading attachment - layer {layer_id}, object ID {object_id}, attachment ID {attachment_id}")
        
        token = self.get_token()

        url = f"{self.feature_service_url}/{layer_id}/{object_id}/attachments/{attachment_id}"
        params = {'token': token}
        logger.debug(f"Attachment download URL: {url}")

        try:
            logger.debug("Sending attachment download request to ArcGIS")
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=60,
            )

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                content_length = len(response.content)
                logger.info(f"Successfully downloaded attachment {attachment_id}: {content_length} bytes, type: {content_type}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                return response.content, content_type
            else:
                logger.error(f"Attachment retrieval failed with status {response.status_code} for attachment {attachment_id}")
                return None, None

        except requests.RequestException as e:
            logger.error(f"Attachment download failed for layer {layer_id}, object ID {object_id}, attachment ID {attachment_id}: {str(e)}", exc_info=True)
            return None, None


class ArcGISError(Exception):
    """Exception raised for ArcGIS API errors."""
    pass


# Singleton instance for convenience
_arcgis_service = None


def get_arcgis_service() -> ArcGISService:
    """Get the singleton ArcGIS service instance."""
    global _arcgis_service
    if _arcgis_service is None:
        _arcgis_service = ArcGISService()
    return _arcgis_service


# Convenience functions matching PHP function names
def get_arcgis_token() -> str:
    """Get ArcGIS authentication token."""
    return get_arcgis_service().get_token()


def query_feature_layer(layer_id: int, where: str = "1=1") -> dict:
    """Query a feature layer."""
    return get_arcgis_service().query_layer(layer_id, where)


def get_attachments(layer_id: int, object_id: int) -> dict:
    """Get attachments for a feature."""
    return get_arcgis_service().get_attachments(layer_id, object_id)
