# Pickle Deserialization with Source

## Vulnerability
The application base64-decodes attacker input and passes it into `pickle.loads`.

## Reconnaissance
The error path exposed enough stack trace to confirm Python pickle deserialization on the backend.

## Exploitation
We define a gadget class whose `__reduce__` returns `os.system`, then serialize it and send the payload.

```python
payload = base64.b64encode(pickle.dumps(RCE())).decode()
```

## Notes
This package includes both the main solver and the helper gadget source as local attachments.
