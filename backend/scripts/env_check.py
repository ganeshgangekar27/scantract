#!/usr/bin/env python3
import os

jwt_secret = os.getenv("JWT_SECRET", "")
reset_mode = os.getenv("RESET_LINK_MODE", "")

print(f"JWT_SECRET_LENGTH: {len(jwt_secret)}")
print(f"RESET_LINK_MODE: {reset_mode}")
