"""
Admin endpoint to trigger realistic One8 data seeding.

Usage from Railway:
  curl -X POST https://your-railway-url.up.railway.app/admin/seed-one8-realistic \
    -H "Authorization: Bearer <super_admin_token>"
"""

import subprocess
import sys
from pathlib import Path

def trigger_realistic_seed():
    """Trigger realistic One8 data seeding script."""
    script_path = Path(__file__).parent.parent / "scripts" / "seed_one8_realistic.py"
    
    # Run the seeding script
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )
    
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
