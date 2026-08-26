import os
import sys
import subprocess
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth import get_demo_merchant

router = APIRouter()

@router.post("/reset")
def reset_demo_state(db: Session = Depends(get_db)):
    merchant = get_demo_merchant(db)
    
    # Check if DEMO_MODE is true
    if os.getenv("DEMO_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Reset is only available in DEMO_MODE")
    
    try:
        # We will run the seed script which handles everything.
        # We use subprocess to run python -m app.db.seed
        result = subprocess.run(
            [sys.executable, "-m", "app.db.seed"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")),
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "success", "message": "Demo state reset successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Seed failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
