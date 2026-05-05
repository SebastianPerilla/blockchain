"""Reads the Hardhat artifact and writes a lean abi.json for the Streamlit app."""
import json, pathlib, sys

ARTIFACT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "artifacts/contracts/LoyaltyToken.sol/LoyaltyToken.json"
)
OUT = pathlib.Path(__file__).resolve().parent / "abi.json"

if not ARTIFACT.exists():
    sys.exit(f"Artifact not found at {ARTIFACT}. Run `npx hardhat compile` first.")

artifact = json.loads(ARTIFACT.read_text())
OUT.write_text(json.dumps(artifact["abi"], indent=2))
print(f"ABI written to {OUT}")
