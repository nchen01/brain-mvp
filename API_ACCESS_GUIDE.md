# API Access Guide

This guide explains how to allow external users or applications to call the Brain MVP API.

## 1. Network Accessibility

By default, the system is configured to listen on all network interfaces (`0.0.0.0`), which means it can be accessed by any device that can reach your machine's IP address.

### Find your IP Address
To allow someone else to call your API, you need to give them your local IP address (if they are on the same network) or your public IP address (if they are calling from the internet).

**On macOS/Linux:**
```bash
ipconfig getifaddr en0  # For Wi-Fi
# OR
curl ifconfig.me        # For Public IP
```

### Access URL
If your IP is `192.168.1.50`, the API will be accessible at:
`http://192.168.1.50:8080`

---

## 2. Interactive Documentation (Swagger)

The easiest way for someone to explore and test the API is through the built-in Swagger UI:
`http://<YOUR_IP>:8080/docs`

This provides a full list of endpoints, request/response schemas, and a "Try it out" button for every request.

---

## 3. Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints allow optional authentication, but some may require it for specific actions.

### Default Credentials
For testing purposes, a default admin user is created:
- **Username**: `admin`
- **Password**: `admin123`

### How to Authenticate
1. **Login**: Call the login endpoint to get a token.
   ```bash
   curl -X POST "http://<YOUR_IP>:8080/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```
2. **Use the Token**: Include the token in the `Authorization` header for subsequent requests.
   ```bash
   curl -X GET "http://<YOUR_IP>:8080/api/v1/documents/" \
     -H "Authorization: Bearer <YOUR_TOKEN>"
   ```

---

## 4. CORS (Cross-Origin Resource Sharing)

The API is configured with `allow_origins=["*"]`, which means:
- Any web application (React, Vue, etc.) can make requests to this API from any domain.
- No additional configuration is needed for frontend developers to start using your API.

---

## 5. Security Considerations

> [!WARNING]
> The current setup is designed for **development and internal testing**.
> Before exposing this to the public internet:
> 1. **Change the JWT Secret**: Update `JWT_SECRET` in `src/api/routers/auth.py`.
> 2. **Change Admin Password**: Use the API to change the default password.
> 3. **Enable HTTPS**: Use a reverse proxy like Nginx or Caddy to handle SSL/TLS.
> 4. **Firewall**: Ensure only port `8080` is open to the public.
