# Robot-Tech

## Local
```
python3.10 -m venv venv
source venv/bin/activate
pip install -r robot-tech/requirements-server.txt
cd robot-tech
uvicorn cloud_api.ai_main:app --reload
```

## Client
```
pip install -r robot-tech/requirements-client.txt
python robot-tech/client/main.py
```

## Docker
```
docker-compose -f robot-tech/docker/docker-compose.yml up
```

## APK
```
buildozer -v android debug
```