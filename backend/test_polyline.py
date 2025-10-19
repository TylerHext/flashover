"""Test polyline decoding."""

import sys
sys.path.insert(0, '/Users/tylerhext/repositories/flashover/backend')

from app.services.polyline import decode_polyline

# Sample polyline from activity 1
polyline = "ciwmEt~rqU@hAOPgEIO@MNMl@Bd@CRH~@BjCCnBB`CGVUD{AEuA?KBILBpEBl@C`LBLLB`Gs@LBFLR|@v@|BtAfFKJc@N}BjAIJC"

print("Testing polyline decoder...")
print(f"Polyline: {polyline[:50]}...")

try:
    coords = decode_polyline(polyline)
    print(f"✓ Decoded {len(coords)} coordinates")
    print(f"First 5 coords: {coords[:5]}")
    print(f"Lat range: {min(c[1] for c in coords):.6f} to {max(c[1] for c in coords):.6f}")
    print(f"Lng range: {min(c[0] for c in coords):.6f} to {max(c[0] for c in coords):.6f}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
