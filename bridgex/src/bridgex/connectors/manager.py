"""
Connector Manager - Unified interface for external system integration.
Provides standardized connectors for APIs, databases, messaging, and more.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, HttpUrl, SecretStr

from bridgex.utils.exceptions import BridgeXError, ConnectionError

logger = logging.getLogger(__name__)


class ConnectorConfig(BaseModel):
    """Configuration for a connector."""
    name: str
    type: str
    base_url: Optional[HttpUrl] = None
    api_key: Optional[SecretStr] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    token: Optional[SecretStr] = None
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay_seconds: int = Field(default=1)
    verify_ssl: bool = Field(default=True)
    additional_headers: Dict[str, str] = Field(default_factory=dict)
    additional_params: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectionStatus(BaseModel):
    """Status of a connector connection."""
    connected: bool
    last_check: str = Field(default_factory=lambda: str(datetime.now().isoformat()))
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ConnectorCapability(BaseModel):
    """Capability of a connector."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    rate_limit: Optional[int] = None  # requests per second
    requires_authentication: bool = Field(default=True)


class ConnectorMetadata(BaseModel):
    """Metadata for a connector."""
    name: str
    version: str = Field(default="1.0.0")
    description: str
    author: str
    supported_versions: List[str] = Field(default_factory=list)
    capabilities: List[ConnectorCapability] = Field(default_factory=list)
    health_endpoint: Optional[str] = None
    documentation_url: Optional[HttpUrl] = None
    tags: List[str] = Field(default_factory=list)


class ConnectorInstance(BaseModel):
    """Instance of a connector."""
    config: ConnectorConfig
    metadata: ConnectorMetadata
    status: ConnectionStatus = Field(default_factory=lambda: ConnectionStatus(connected=False))
    last_used: Optional[str] = None
    usage_count: int = 0
    created_at: str = Field(default_factory=lambda: str(datetime.now().isoformat()))


class BaseConnector:
    """Base class for all connectors.
    
    All connectors should inherit from this class and implement the required methods.
    """
    
    def __init__(self, config: ConnectorConfig):
        """Initialize the connector.
        
        Args:
            config: Connector configuration
        """
        self.config = config
        self.metadata = self._get_metadata()
        self.client = None
        self.logger = logging.getLogger(f"connector.{config.name}")
    
    def _get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            Connector metadata
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_metadata")
    
    async def connect(self) -> bool:
        """Establish connection to the external system.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
        """
        raise NotImplementedError("Subclasses must implement connect")
    
    async def disconnect(self) -> bool:
        """Disconnect from the external system.
        
        Returns:
            True if disconnection successful
        """
        raise NotImplementedError("Subclasses must implement disconnect")
    
    async def health_check(self) -> ConnectionStatus:
        """Check the health of the connection.
        
        Returns:
            Connection status
        """
        raise NotImplementedError("Subclasses must implement health_check")
    
    async def execute(
        self,
        capability: str,
        params: Dict[str, Any],
    ) -> Any:
        """Execute a connector capability.
        
        Args:
            capability: Name of the capability to execute
            params: Parameters for the capability
            
        Returns:
            Execution result
            
        Raises:
            BridgeXError: If capability not found or execution fails
        """
        raise NotImplementedError("Subclasses must implement execute")
    
    async def test_connection(self) -> bool:
        """Test the connection to the external system.
        
        Returns:
            True if test successful
        """
        try:
            await self.connect()
            status = await self.health_check()
            return status.connected
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
        finally:
            await self.disconnect()


class ConnectorManager:
    """Manages all connectors and provides unified interface.
    
    Features:
    - Connector lifecycle management
    - Connection pooling
    - Automatic retry and error handling
    - Rate limiting
    - Health monitoring
    - Unified authentication
    """
    
    def __init__(self, max_connections: int = 50):
        """Initialize the connector manager.
        
        Args:
            max_connections: Maximum number of concurrent connections
        """
        self.max_connections = max_connections
        self.connectors: Dict[str, ConnectorInstance] = {}
        self.active_connections: Dict[str, BaseConnector] = {}
        self.connector_registry: Dict[str, Type[BaseConnector]] = {}
        
        # Load built-in connectors
        self._load_builtin_connectors()
        
        logger.info(f"Connector Manager initialized (max connections: {max_connections})")
    
    async def initialize(self) -> None:
        """Initialize the connector manager."""
        logger.info("Connector Manager initialization complete")
    
    def register_connector(
        self,
        connector_type: str,
        connector_class: Type[BaseConnector],
    ) -> None:
        """Register a connector type.
        
        Args:
            connector_type: Type identifier for the connector
            connector_class: Connector class
            
        Raises:
            BridgeXError: If connector type already registered
        """
        if connector_type in self.connector_registry:
            raise BridgeXError(f"Connector type already registered: {connector_type}")
        
        self.connector_registry[connector_type] = connector_class
        logger.info(f"Connector type registered: {connector_type}")
    
    async def create_connector(
        self,
        config: ConnectorConfig,
        test_connection: bool = True,
    ) -> str:
        """Create a new connector instance.
        
        Args:
            config: Connector configuration
            test_connection: Whether to test connection on creation
            
        Returns:
            Connector ID
            
        Raises:
            BridgeXError: If connector type not found or limit reached
        """
        # Check if connector type is registered
        if config.type not in self.connector_registry:
            raise BridgeXError(f"Connector type not found: {config.type}")
        
        # Check connection limit
        if len(self.connectors) >= self.max_connections:
            # Clean up inactive connectors
            await self._cleanup_inactive_connectors()
            
            if len(self.connectors) >= self.max_connections:
                raise BridgeXError(f"Maximum connector limit reached: {self.max_connections}")
        
        # Create connector instance
        connector_class = self.connector_registry[config.type]
        connector = connector_class(config)
        
        # Get metadata
        metadata = connector.metadata
        
        # Create instance record
        instance = ConnectorInstance(
            config=config,
            metadata=metadata,
        )
        
        connector_id = f"{config.type}:{config.name}"
        self.connectors[connector_id] = instance
        
        # Test connection if requested
        if test_connection:
            try:
                connected = await connector.test_connection()
                instance.status.connected = connected
                instance.status.last_check = str(datetime.now().isoformat())
                
                if not connected:
                    logger.warning(f"Connector {connector_id} connection test failed")
            except Exception as e:
                logger.error(f"Connector {connector_id} connection test error: {e}")
                instance.status.connected = False
                instance.status.error = str(e)
        
        logger.info(f"Connector created: {connector_id}")
        return connector_id
    
    async def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        """Get a connector instance, creating connection if needed.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            Connector instance or None if not found
        """
        if connector_id not in self.connectors:
            return None
        
        instance = self.connectors[connector_id]
        
        # Check if already active
        if connector_id in self.active_connections:
            connector = self.active_connections[connector_id]
            
            # Verify connection is still healthy
            try:
                status = await connector.health_check()
                if status.connected:
                    instance.status = status
                    instance.last_used = str(datetime.now().isoformat())
                    instance.usage_count += 1
                    return connector
            except Exception:
                # Connection may be broken, will reconnect below
                pass
        
        # Create new connection
        connector_class = self.connector_registry[instance.config.type]
        connector = connector_class(instance.config)
        
        try:
            # Connect
            connected = await connector.connect()
            if not connected:
                raise ConnectionError(f"Failed to connect to {connector_id}")
            
            # Store active connection
            self.active_connections[connector_id] = connector
            
            # Update instance
            instance.status.connected = True
            instance.status.last_check = str(datetime.now().isoformat())
            instance.last_used = str(datetime.now().isoformat())
            instance.usage_count += 1
            
            logger.info(f"Connector connected: {connector_id}")
            return connector
            
        except Exception as e:
            logger.error(f"Failed to get connector {connector_id}: {e}")
            instance.status.connected = False
            instance.status.error = str(e)
            return None
    
    async def execute(
        self,
        connector_id: str,
        capability: str,
        params: Dict[str, Any],
        retry_on_failure: bool = True,
    ) -> Any:
        """Execute a capability through a connector.
        
        Args:
            connector_id: Connector ID
            capability: Capability name
            params: Parameters for the capability
            retry_on_failure: Whether to retry on failure
            
        Returns:
            Execution result
            
        Raises:
            BridgeXError: If connector not found or execution fails
        """
        connector = await self.get_connector(connector_id)
        if not connector:
            raise BridgeXError(f"Connector not found or not connected: {connector_id}")
        
        instance = self.connectors[connector_id]
        
        # Check if capability exists
        capability_metadata = None
        for cap in instance.metadata.capabilities:
            if cap.name == capability:
                capability_metadata = cap
                break
        
        if not capability_metadata:
            raise BridgeXError(
                f"Capability not found: {capability} for connector {connector_id}"
            )
        
        # Validate parameters against schema
        self._validate_params(params, capability_metadata.input_schema)
        
        # Execute with retry
        max_retries = instance.config.max_retries if retry_on_failure else 0
        
        for attempt in range(max_retries + 1):
            try:
                result = await connector.execute(capability, params)
                
                # Update usage
                instance.last_used = str(datetime.now().isoformat())
                instance.usage_count += 1
                
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    delay = instance.config.retry_delay_seconds * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Execution attempt {attempt + 1} failed for {connector_id}.{capability}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All execution attempts failed for {connector_id}.{capability}: {e}"
                    )
                    instance.status.error = str(e)
                    raise BridgeXError(
                        f"Execution failed for {connector_id}.{capability}: {e}"
                    ) from e
    
    async def health_check_all(self) -> Dict[str, ConnectionStatus]:
        """Check health of all connectors.
        
        Returns:
            Dictionary of connector IDs to connection status
        """
        results = {}
        
        for connector_id in list(self.connectors.keys()):
            try:
                status = await self.health_check(connector_id)
                results[connector_id] = status
            except Exception as e:
                logger.error(f"Health check failed for {connector_id}: {e}")
                results[connector_id] = ConnectionStatus(
                    connected=False,
                    error=str(e),
                )
        
        return results
    
    async def health_check(self, connector_id: str) -> ConnectionStatus:
        """Check health of a specific connector.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            Connection status
        """
        if connector_id not in self.connectors:
            raise BridgeXError(f"Connector not found: {connector_id}")
        
        instance = self.connectors[connector_id]
        
        # Try to get connector
        connector = await self.get_connector(connector_id)
        if not connector:
            return ConnectionStatus(
                connected=False,
                error="Failed to get connector",
            )
        
        try:
            # Perform health check
            start_time = datetime.now()
            status = await connector.health_check()
            end_time = datetime.now()
            
            # Calculate latency
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            status.latency_ms = latency_ms
            
            # Update instance
            instance.status = status
            
            return status
            
        except Exception as e:
            logger.error(f"Health check failed for {connector_id}: {e}")
            
            status = ConnectionStatus(
                connected=False,
                error=str(e),
            )
            
            instance.status = status
            return status
    
    async def disconnect(self, connector_id: str) -> bool:
        """Disconnect a connector.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            True if disconnected successfully
        """
        if connector_id not in self.active_connections:
            return False
        
        connector = self.active_connections[connector_id]
        
        try:
            await connector.disconnect()
            del self.active_connections[connector_id]
            
            if connector_id in self.connectors:
                self.connectors[connector_id].status.connected = False
            
            logger.info(f"Connector disconnected: {connector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect connector {connector_id}: {e}")
            return False
    
    async def remove_connector(self, connector_id: str) -> bool:
        """Remove a connector instance.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            True if removed successfully
        """
        # Disconnect first
        await self.disconnect(connector_id)
        
        # Remove from connectors
        if connector_id in self.connectors:
            del self.connectors[connector_id]
            logger.info(f"Connector removed: {connector_id}")
            return True
        
        return False
    
    def list_connectors(
        self,
        connector_type: Optional[str] = None,
        connected_only: bool = False,
    ) -> List[ConnectorInstance]:
        """List all connector instances.
        
        Args:
            connector_type: Filter by connector type
            connected_only: Only return connected connectors
            
        Returns:
            List of connector instances
        """
        instances = list(self.connectors.values())
        
        if connector_type:
            instances = [
                i for i in instances
                if i.config.type == connector_type
            ]
        
        if connected_only:
            instances = [
                i for i in instances
                if i.status.connected
            ]
        
        return instances
    
    def get_connector_types(self) -> List[str]:
        """Get all registered connector types.
        
        Returns:
            List of connector type names
        """
        return list(self.connector_registry.keys())
    
    def _validate_params(
        self,
        params: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> None:
        """Validate parameters against a schema.
        
        Args:
            params: Parameters to validate
            schema: Schema to validate against
            
        Raises:
            BridgeXError: If validation fails
        """
        for param_name, param_schema in schema.items():
            if isinstance(param_schema, dict):
                required = param_schema.get('required', False)
                param_type = param_schema.get('type', 'string')
                
                if required and param_name not in params:
                    raise BridgeXError(
                        f"Missing required parameter: {param_name}"
                    )
                
                if param_name in params:
                    value = params[param_name]
                    
                    # Type checking
                    type_map = {
                        'string': str,
                        'number': (int, float),
                        'integer': int,
                        'boolean': bool,
                        'array': list,
                        'object': dict,
                    }
                    
                    expected_type = type_map.get(param_type)
                    if expected_type and not isinstance(value, expected_type):
                        raise BridgeXError(
                            f"Parameter {param_name}: expected {param_type}, "
                            f"got {type(value).__name__}"
                        )
    
    async def _cleanup_inactive_connectors(self) -> None:
        """Clean up connectors that have been inactive for too long."""
        cutoff = datetime.now() - timedelta(hours=1)  # 1 hour inactive
        
        to_remove = []
        for connector_id, instance in self.connectors.items():
            if instance.last_used:
                last_used = datetime.fromisoformat(instance.last_used)
                if last_used < cutoff:
                    to_remove.append(connector_id)
        
        for connector_id in to_remove:
            await self.remove_connector(connector_id)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive connectors")
    
    def _load_builtin_connectors(self) -> None:
        """Load built-in connector types."""
        # REST API Connector
        class RESTConnector(BaseConnector):
            def _get_metadata(self) -> ConnectorMetadata:
                return ConnectorMetadata(
                    name="REST API Connector",
                    description="Generic REST API connector with HTTP methods",
                    author="BridgeX",
                    capabilities=[
                        ConnectorCapability(
                            name="get",
                            description="HTTP GET request",
                            input_schema={
                                "endpoint": {"type": "string", "required": True},
                                "params": {"type": "object", "required": False},
                                "headers": {"type": "object", "required": False},
                            },
                            output_schema={
                                "status_code": "integer",
                                "headers": "object",
                                "body": "any",
                            },
                        ),
                        ConnectorCapability(
                            name="post",
                            description="HTTP POST request",
                            input_schema={
                                "endpoint": {"type": "string", "required": True},
                                "data": {"type": "any", "required": True},
                                "headers": {"type": "object", "required": False},
                            },
                            output_schema={
                                "status_code": "integer",
                                "headers": "object",
                                "body": "any",
                            },
                        ),
                        ConnectorCapability(
                            name="put",
                            description="HTTP PUT request",
                            input_schema={
                                "endpoint": {"type": "string", "required": True},
                                "data": {"type": "any", "required": True},
                                "headers": {"type": "object", "required": False},
                            },
                            output_schema={
                                "status_code": "integer",
                                "headers": "object",
                                "body": "any",
                            },
                        ),
                        ConnectorCapability(
                            name="delete",
                            description="HTTP DELETE request",
                            input_schema={
                                "endpoint": {"type": "string", "required": True},
                                "headers": {"type": "object", "required": False},
                            },
                            output_schema={
                                "status_code": "integer",
                                "headers": "object",
                                "body": "any",
                            },
                        ),
                    ],
                    health_endpoint="/health",
                    tags=["http", "api", "rest"],
                )
            
            async def connect(self) -> bool:
                import httpx
                
                try:
                    # Create HTTP client
                    self.client = httpx.AsyncClient(
                        base_url=str(self.config.base_url) if self.config.base_url else None,
                        timeout=self.config.timeout_seconds,
                        verify=self.config.verify_ssl,
                        headers=self._build_headers(),
                    )
                    
                    # Test connection
                    if self.config.base_url and self.metadata.health_endpoint:
                        try:
                            response = await self.client.get(self.metadata.health_endpoint)
                            return response.status_code < 500
                        except Exception:
                            # Health endpoint may not exist, but client is created
                            return True
                    
                    return True
                    
                except Exception as e:
                    self.logger.error(f"Failed to connect: {e}")
                    return False
            
            async def disconnect(self) -> bool:
                if self.client:
                    try:
                        await self.client.aclose()
                        self.client = None
                        return True
                    except Exception as e:
                        self.logger.error(f"Failed to disconnect: {e}")
                        return False
                return True
            
            async def health_check(self) -> ConnectionStatus:
                if not self.client:
                    return ConnectionStatus(
                        connected=False,
                        error="Not connected",
                    )
                
                try:
                    start_time = datetime.now()
                    
                    # Try a simple request
                    test_endpoint = self.metadata.health_endpoint or "/"
                    response = await self.client.get(test_endpoint)
                    
                    end_time = datetime.now()
                    latency_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    return ConnectionStatus(
                        connected=response.status_code < 500,
                        latency_ms=latency_ms,
                        details={
                            "status_code": response.status_code,
                            "url": str(response.url),
                        },
                    )
                    
                except Exception as e:
                    return ConnectionStatus(
                        connected=False,
                        error=str(e),
                    )
            
            async def execute(self, capability: str, params: Dict[str, Any]) -> Any:
                if not self.client:
                    raise ConnectionError("Not connected")
                
                method_map = {
                    "get": self.client.get,
                    "post": self.client.post,
                    "put": self.client.put,
                    "delete": self.client.delete,
                }
                
                if capability not in method_map:
                    raise BridgeXError(f"Unsupported capability: {capability}")
                
                method = method_map[capability]
                endpoint = params.get("endpoint", "")
                
                # Build request
                request_kwargs = {}
                
                if "headers" in params:
                    request_kwargs["headers"] = params["headers"]
                
                if capability in ["post", "put"] and "data" in params:
                    request_kwargs["json"] = params["data"]
                
                if capability == "get" and "params" in params:
                    request_kwargs["params"] = params["params"]
                
                # Execute request
                try:
                    response = await method(endpoint, **request_kwargs)
                    
                    # Parse response
                    try:
                        body = response.json()
                    except Exception:
                        body = response.text
                    
                    return {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": body,
                    }
                    
                except Exception as e:
                    raise BridgeXError(f"Request failed: {e}") from e
            
            def _build_headers(self) -> Dict[str, str]:
                """Build default headers from config."""
                headers = {}
                
                # Add authentication headers
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"
                elif self.config.token:
                    headers["Authorization"] = f"Bearer {self.config.token.get_secret_value()}"
                elif self.config.username and self.config.password:
                    import base64
                    auth_str = f"{self.config.username}:{self.config.password.get_secret_value()}"
                    auth_bytes = auth_str.encode('ascii')
                    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                    headers["Authorization"] = f"Basic {auth_b64}"
                
                # Add additional headers
                headers.update(self.config.additional_headers)
                
                return headers
        
        # Database Connector (PostgreSQL example)
        class DatabaseConnector(BaseConnector):
            def _get_metadata(self) -> ConnectorMetadata:
                return ConnectorMetadata(
                    name="Database Connector",
                    description="Generic database connector (PostgreSQL, MySQL, SQLite)",
                    author="BridgeX",
                    capabilities=[
                        ConnectorCapability(
                            name="query",
                            description="Execute SQL query",
                            input_schema={
                                "sql": {"type": "string", "required": True},
                                "params": {"type": "array", "required": False},
                            },
                            output_schema={
                                "rows": "array",
                                "rowcount": "integer",
                                "columns": "array",
                            },
                        ),
                        ConnectorCapability(
                            name="execute",
                            description="Execute SQL statement",
                            input_schema={
                                "sql": {"type": "string", "required": True},
                                "params": {"type": "array", "required": False},
                            },
                            output_schema={
                                "rowcount": "integer",
                            },
                        ),
                        ConnectorCapability(
                            name="transaction",
                            description="Execute multiple statements in a transaction",
                            input_schema={
                                "statements": {"type": "array", "required": True},
                            },
                            output_schema={
                                "results": "array",
                                "success": "boolean",
                            },
                        ),
                    ],
                    tags=["database", "sql", "postgresql", "mysql", "sqlite"],
                )
            
            async def connect(self) -> bool:
                try:
                    # This is a simplified implementation
                    # In a real implementation, this would create a database connection
                    self.client = {"connected": True}
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to connect to database: {e}")
                    return False
            
            async def disconnect(self) -> bool:
                if self.client:
                    self.client = None
                return True
            
            async def health_check(self) -> ConnectionStatus:
                if not self.client:
                    return ConnectionStatus(connected=False, error="Not connected")
                
                try:
                    # Simple health check
                    return ConnectionStatus(connected=True)
                except Exception as e:
                    return ConnectionStatus(connected=False, error=str(e))
            
            async def execute(self, capability: str, params: Dict[str, Any]) -> Any:
                if not self.client:
                    raise ConnectionError("Not connected")
                
                # Simplified implementation
                if capability == "query":
                    return {
                        "rows": [],
                        "rowcount": 0,
                        "columns": [],
                    }
                elif capability == "execute":
                    return {"rowcount": 1}
                elif capability == "transaction":
                    return {
                        "results": [],
                        "success": True,
                    }
                else:
                    raise BridgeXError(f"Unsupported capability: {capability}")
        
        # Register built-in connectors
        self.register_connector("rest", RESTConnector)
        self.register_connector("database", DatabaseConnector)
        
        logger.info("Built-in connectors loaded")
    
    async def shutdown(self) -> None:
        """Shutdown the connector manager."""
        # Disconnect all active connections
        for connector_id in list(self.active_connections.keys()):
            await self.disconnect(connector_id)
        
        logger.info("Connector Manager shutdown complete")


# Import here to avoid circular import
from datetime import datetime, timedelta