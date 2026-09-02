import re
import os
from fastapi.testclient import TestClient
from app.main import app

def test_frontend_backend_route_drift():
    client = TestClient(app)
    api_ts_path = os.path.join(os.path.dirname(__file__), '../../frontend/lib/api.ts')
    
    with open(api_ts_path, 'r') as f:
        content = f.read()
        
    # Extract paths used with API_BASE
    # e.g. `${API_BASE}/agent/chat`
    matches = re.findall(r'\$\{API_BASE\}([^`"\'?]+)', content)
    
    # Also find paths that have query params directly in them but we only want the path
    # Actually the regex above stops at ? so it handles query params!
    
    valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
    tested_paths = set()
    
    for match in matches:
        path = match.strip()
        if not path:
            continue
            
        # Replace TS variables like ${id} or ${cartId} with a valid UUID
        # to pass FastAPI's path validation
        path = re.sub(r'\$\{[^}]+\}', valid_uuid, path)
        
        # In case the regex caught something weird or empty
        if path in tested_paths:
            continue
            
        tested_paths.add(path)
        
        # Use OPTIONS request
        response = client.options(f"/api{path}")
        
        # If it's a real route, OPTIONS usually returns 200 (if CORS handles it) 
        # or 405 Method Not Allowed (if CORS doesn't and route exists)
        # or 401/403 if there's global auth middleware that runs first
        # But it will NOT return 404 if the route exists.
        assert response.status_code != 404, f"Drift detected! Frontend calls /api{path} but backend returned 404."

    print(f"Successfully validated {len(tested_paths)} frontend API paths against backend routes.")

if __name__ == "__main__":
    test_frontend_backend_route_drift()
