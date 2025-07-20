"""
Integration tests for module management API endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Mock the dependencies before importing main
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock Redis before importing
class MockRedis:
    async def ping(self): return True
    async def publish(self, *args, **kwargs): return 1
    async def subscribe(self, *args, **kwargs): return AsyncMock()
    async def close(self): pass

with patch('redis.Redis', return_value=MockRedis()):
    from backend.main import app
    from backend.core.module_loader import ModuleLoader, ModuleState


@pytest.mark.asyncio
class TestModuleAPIEndpoints:
    """Test module management API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
        
    @pytest.fixture
    async def mock_loader(self):
        """Mock module loader fixture"""
        loader = AsyncMock(spec=ModuleLoader)
        loader.get_module_list.return_value = [
            {
                "name": "test_module",
                "state": "ready",
                "loaded": True,
                "error": None,
                "reload_count": 0,
                "dependencies": [],
                "module_info": {
                    "name": "test_module",
                    "state": "ready",
                    "routes": 1,
                    "dependencies": [],
                    "dependents": [],
                    "tasks": 0
                }
            }
        ]
        loader.get_stats.return_value = {
            "loaded_modules": 1,
            "total_modules": 1,
            "failed_modules": 0,
            "state_counts": {"ready": 1},
            "total_reloads": 0
        }
        return loader
        
    def test_get_modules_endpoint(self, client, mock_loader):
        """Test GET /api/modules endpoint"""
        with patch('backend.main.module_loader', mock_loader):
            response = client.get("/api/modules")
            
        assert response.status_code == 200
        data = response.json()
        
        assert "modules" in data
        assert "stats" in data
        assert len(data["modules"]) == 1
        assert data["modules"][0]["name"] == "test_module"
        assert data["stats"]["loaded_modules"] == 1
        
    def test_get_modules_no_loader(self, client):
        """Test GET /api/modules with no loader"""
        with patch('backend.main.module_loader', None):
            response = client.get("/api/modules")
            
        assert response.status_code == 200
        data = response.json()
        assert data["modules"] == []
        assert data["stats"] == {}
        
    def test_reload_module_endpoint(self, client, mock_loader):
        """Test POST /api/modules/{module_name}/reload endpoint"""
        mock_loader.reload_module.return_value = None
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/test_module/reload")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test_module reloaded" in data["message"]
        mock_loader.reload_module.assert_called_once_with("test_module", force=False)
        
    def test_reload_module_with_force(self, client, mock_loader):
        """Test reload module with force parameter"""
        mock_loader.reload_module.return_value = None
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/test_module/reload?force=true")
            
        assert response.status_code == 200
        mock_loader.reload_module.assert_called_once_with("test_module", force=True)
        
    def test_reload_module_error(self, client, mock_loader):
        """Test reload module with error"""
        mock_loader.reload_module.side_effect = Exception("Reload failed")
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/test_module/reload")
            
        assert response.status_code == 500
        data = response.json()
        assert "Reload failed" in data["detail"]
        
    def test_reload_module_no_loader(self, client):
        """Test reload module with no loader"""
        with patch('backend.main.module_loader', None):
            response = client.post("/api/modules/test_module/reload")
            
        assert response.status_code == 503
        data = response.json()
        assert "Module loader not available" in data["detail"]
        
    def test_unload_module_endpoint(self, client, mock_loader):
        """Test POST /api/modules/{module_name}/unload endpoint"""
        mock_loader.unload_module.return_value = None
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/test_module/unload")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test_module unloaded" in data["message"]
        mock_loader.unload_module.assert_called_once_with("test_module", force=False)
        
    def test_unload_module_with_force(self, client, mock_loader):
        """Test unload module with force parameter"""
        mock_loader.unload_module.return_value = None
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/test_module/unload?force=true")
            
        assert response.status_code == 200
        mock_loader.unload_module.assert_called_once_with("test_module", force=True)
        
    def test_reload_all_modules_endpoint(self, client, mock_loader):
        """Test POST /api/modules/reload-all endpoint"""
        mock_loader.reload_all_modules.return_value = {"test_module": "success"}
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/reload-all")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["results"]["test_module"] == "success"
        mock_loader.reload_all_modules.assert_called_once_with(force=False)
        
    def test_reload_all_modules_with_force(self, client, mock_loader):
        """Test reload all modules with force parameter"""
        mock_loader.reload_all_modules.return_value = {}
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/reload-all?force=true")
            
        assert response.status_code == 200
        mock_loader.reload_all_modules.assert_called_once_with(force=True)
        
    def test_auto_reload_modules_endpoint(self, client, mock_loader):
        """Test POST /api/modules/auto-reload endpoint"""
        mock_loader.auto_reload_changed_modules.return_value = {"test_module": "success"}
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.post("/api/modules/auto-reload")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["results"]["test_module"] == "success"
        
    def test_check_module_changes_endpoint(self, client, mock_loader):
        """Test GET /api/modules/changes endpoint"""
        mock_loader.check_file_changes.return_value = {"test_module": True}
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.get("/api/modules/changes")
            
        assert response.status_code == 200
        data = response.json()
        assert data["changes"]["test_module"] is True
        assert data["changed_count"] == 1
        
    def test_get_dependency_graph_endpoint(self, client, mock_loader):
        """Test GET /api/modules/dependency-graph endpoint"""
        mock_loader.get_module_dependency_graph.return_value = {
            "dependencies": {"test_module": []},
            "dependents": {"test_module": []}
        }
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.get("/api/modules/dependency-graph")
            
        assert response.status_code == 200
        data = response.json()
        assert "graph" in data
        assert "dependencies" in data["graph"]
        assert "dependents" in data["graph"]
        
    def test_get_module_routes_endpoint(self, client, mock_loader):
        """Test GET /api/modules/routes endpoint"""
        mock_loader.list_module_routes.return_value = {
            "test_module": ["['GET'] /test"]
        }
        
        with patch('backend.main.module_loader', mock_loader):
            response = client.get("/api/modules/routes")
            
        assert response.status_code == 200
        data = response.json()
        assert "routes" in data
        assert "test_module" in data["routes"]
        assert len(data["routes"]["test_module"]) == 1
        
    def test_health_endpoint(self, client):
        """Test health endpoint still works"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
    def test_status_endpoint(self, client):
        """Test status endpoint integration"""
        with patch('backend.main.module_loader') as mock_loader, \
             patch('backend.main.worker_manager') as mock_worker, \
             patch('backend.main.websocket_manager') as mock_ws:
            
            mock_loader.get_stats.return_value = {"loaded_modules": 1}
            mock_worker.workers = {"test_worker": AsyncMock()}
            mock_ws.connection_count = 2
            
            response = client.get("/api/status")
            
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "modules" in data
        assert "workers" in data
        assert "connections" in data


@pytest.mark.asyncio 
class TestModuleAPIIntegration:
    """Integration tests combining real module loader with API"""
    
    @pytest.fixture
    async def real_loader(self, started_event_bus):
        """Real module loader fixture"""
        return ModuleLoader(started_event_bus)
        
    async def test_real_module_api_integration(self, real_loader, temp_module_dir):
        """Test API with real module loader"""
        client = TestClient(app)
        
        with patch('backend.main.module_loader', real_loader):
            # Initially no modules
            response = client.get("/api/modules")
            assert response.status_code == 200
            data = response.json()
            assert data["stats"]["loaded_modules"] == 0
            
            # Load a module manually
            module_name = "test_module" 
            module_path = temp_module_dir / module_name
            await real_loader.load_module(module_name, module_path)
            
            # Check API reflects loaded module
            response = client.get("/api/modules")
            assert response.status_code == 200
            data = response.json()
            assert data["stats"]["loaded_modules"] == 1
            assert len(data["modules"]) == 1
            assert data["modules"][0]["name"] == module_name
            
            # Test reload via API
            response = client.post(f"/api/modules/{module_name}/reload?force=true")
            assert response.status_code == 200
            
            # Check reload count increased
            response = client.get("/api/modules")
            data = response.json()
            assert data["modules"][0]["reload_count"] == 1
            
            # Test unload via API
            response = client.post(f"/api/modules/{module_name}/unload")
            assert response.status_code == 200
            
            # Check module unloaded
            response = client.get("/api/modules")
            data = response.json()
            assert data["stats"]["loaded_modules"] == 0