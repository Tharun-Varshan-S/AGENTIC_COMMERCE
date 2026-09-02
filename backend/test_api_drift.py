import re
import sys
import urllib.request
import urllib.error

# This script runs a simple drift check between the frontend's hardcoded paths in api.ts and the backend route table.

API_TS_PATH = "../frontend/lib/api.ts"
BACKEND_URL = "http://localhost:8080" # we know the backend is running on 8080 right now

def extract_endpoints_from_api_ts():
    endpoints = []
    with open(API_TS_PATH, 'r') as f:
        content = f.read()
        
    # Find all strings that look like template literals calling API_BASE
    # e.g. `${API_BASE}/agent/chat`
    matches = re.findall(r'`\$\{API_BASE\}(/[^`]+)`', content)
    
    # Exclude dynamic routes where we can't easily guess the URL parameter 
    # (or we provide a dummy value if we want to be thorough)
    for match in matches:
        # Replace template variables like ${orderId} with a dummy string
        path = re.sub(r'\$\{[^}]+\}', 'dummy_id', match)
        endpoints.append(path)
        
    return list(set(endpoints))

def test_drift():
    endpoints = extract_endpoints_from_api_ts()
    if not endpoints:
        print("No endpoints found in api.ts. Check regex!")
        sys.exit(1)
        
    print(f"Found endpoints in frontend: {endpoints}")
    
    failed = False
    for path in endpoints:
        url = f"{BACKEND_URL}/api{path}" # API_BASE is /api + path
        print(f"Testing {url} ...", end=" ")
        
        req = urllib.request.Request(url, method="OPTIONS")
        try:
            response = urllib.request.urlopen(req)
            print(f"OK ({response.status})")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"FAIL (404 Not Found)")
                failed = True
            else:
                # 401, 405, 422, etc. means the route exists, just method/auth issue
                print(f"OK ({e.code})")
        except urllib.error.URLError as e:
            print(f"FAIL (Connection refused - is backend running?)")
            failed = True
            
    if failed:
        print("\nERROR: API drift detected! Frontend is calling a 404 route.")
        sys.exit(1)
    else:
        print("\nSUCCESS: No API drift detected. All paths are registered in the backend.")

if __name__ == "__main__":
    test_drift()
