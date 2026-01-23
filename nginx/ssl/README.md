# SSL Certificates Directory

This directory holds your SSL certificates for HTTPS.

## Option 1: Let's Encrypt (Recommended - Free)

### Using Certbot:

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d auratask.com -d www.auratask.com

# Certificates will be in: /etc/letsencrypt/live/auratask.com/
# Copy them here:
sudo cp /etc/letsencrypt/live/auratask.com/fullchain.pem ./fullchain.pem
sudo cp /etc/letsencrypt/live/auratask.com/privkey.pem ./privkey.pem
```

### Auto-renewal:
```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for auto-renewal
0 0 1 * * certbot renew && docker-compose -f docker-compose.prod.yml restart nginx
```

## Option 2: Self-Signed (Development/Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=localhost"
```

⚠️ **Warning:** Self-signed certificates will show browser warnings in production.

## Required Files:

- `fullchain.pem` - Certificate chain
- `privkey.pem` - Private key

## Security Notes:

- 🔒 **Never commit** `.pem` files to Git
- 🔐 Set proper permissions: `chmod 600 privkey.pem`
- 🔄 Renew certificates before expiry (Let's Encrypt: every 90 days)
