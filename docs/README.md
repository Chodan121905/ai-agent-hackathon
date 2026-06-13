# docs/

`openapi.json` is exported here from the running backend (the shared contract for the web
and Flutter clients):

```bash
cd ../backend && python -m app           # start it, then:
curl http://localhost:8000/openapi.json -o ../docs/openapi.json
```
