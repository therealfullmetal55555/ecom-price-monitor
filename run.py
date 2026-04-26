#!/usr/bin/env python3
"""
Entry point for portfolio demo
"""
from src.main import run_pipeline

if __name__ == "__main__":
    result = run_pipeline(send_telegram=True)
    print("\n=== RESULT ===")
    for k, v in result.items():
        if k != "alerts":
            print(f"{k}: {v}")
    if result.get("alerts"):
        print("\nCritical alerts:")
        for msg in result["alerts"]:
            print(f" - {msg}")
