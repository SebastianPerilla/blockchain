"""
extract_abi.py
──────────────
Reads the Hardhat artifact for VendingMachine and writes a lean abi.json
that the Streamlit app can import.  Run this once after `npx hardhat compile`.
"""
import json, pathlib, sys

ARTIFACT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "artifacts/contracts/VendingMachine.sol/VendingMachine.json"
)
OUT = pathlib.Path(__file__).resolve().parent / "abi.json"

if not ARTIFACT.exists():
    sys.exit(f"Artifact not found at {ARTIFACT}. Run `npx hardhat compile` first.")

artifact = json.loads(ARTIFACT.read_text())
OUT.write_text(json.dumps(artifact["abi"], indent=2))
print(f"ABI written to {OUT}")
