import os

def is_rooted() -> bool:
    paths = [
        "/system/app/Superuser.apk",
        "/system/xbin/su",
        "/system/bin/su",
        "/system/su",
        "/sbin/su",
        "/su/bin/su",
    ]
    try:
        import subprocess
        for p in paths:
            if os.path.exists(p):
                return True
        out = subprocess.run(["which", "su"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return True
    except Exception:
        pass
    return False