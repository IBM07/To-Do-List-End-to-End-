# 🚀 AuraTask Production Deployment Guide

This guide covers deploying AuraTask securely in production with HTTPS.

---

## 📋 Pre-Deployment Checklist

Before deploying to production, ensure all security measures are in place:

### Environment Configuration

- [ ] `.env` file created in `backend/` directory
- [ ] `ENVIRONMENT=production` set
- [ ] `DEBUG=False` set
- [ ] Strong `SECRET_KEY` generated (32+ characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] `ENCRYPTION_KEY` generated
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- [ ] `CORS_ORIGINS` set to your production domain (e.g., `https://auratask.com`)
- [ ] `DB_PASSWORD` - Strong database password
- [ ] `REDIS_PASSWORD` - Strong Redis password
- [ ] SMTP credentials configured (Gmail App Password or other)
- [ ] Groq API key set (for NLP features)

### Database & Infrastructure

- [ ] MySQL 8.0 configured
- [ ] Redis configured with password
- [ ] Database backups scheduled
- [ ] SSL certificates obtained (Let's Encrypt or commercial)

---

## 🐳 Deployment Option 1: Docker with Nginx (Recommended)

This setup uses Docker Compose with Nginx as a reverse proxy handling SSL termination.

### Step 1: Configure Environment

```bash
# Copy .env.example to .env
cp backend/.env.example backend/.env

# Edit .env with production values
nano backend/.env
```

**Critical settings:**
```env
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<your-generated-32-char-key>
ENCRYPTION_KEY=<your-generated-fernet-key>
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DB_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
```

### Step 2: Obtain SSL Certificates

#### Using Let's Encrypt (Free, Recommended):

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Stop any service using ports 80/443
sudo systemctl stop nginx

# Generate certificates
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  --email your@email.com \
  --agree-tos

# Copy certificates to nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# Set permissions
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem
```

#### Auto-Renewal (Let's Encrypt):

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for automatic renewal every month
crontab -e
# Add this line:
0 0 1 * * certbot renew --quiet && docker-compose -f docker-compose.prod.yml restart nginx
```

### Step 3: Update nginx.conf

Edit `nginx/nginx.conf` and replace `auratask.com` with your actual domain:

```nginx
server_name yourdomain.com www.yourdomain.com;
```

### Step 4: Deploy

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Step 5: Verify Deployment

```bash
# Test HTTPS
curl https://yourdomain.com/health

# Check SSL grade
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

---

## ☁️ Deployment Option 2: Cloud Platforms

Many cloud platforms provide automatic HTTPS. No Nginx or SSL configuration needed!

### Heroku

```bash
# Login
heroku login

# Create app
heroku create auratask

# Add MySQL addon
heroku addons:create jawsdb-maria

# Add Redis addon
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=<your-key>
heroku config:set ENCRYPTION_KEY=<your-key>
heroku config:set CORS_ORIGINS=https://auratask.herokuapp.com

# Deploy
git push heroku main

# Open app
heroku open
```

**HTTPS:** Automatic SSL provided by Heroku.

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up

# Set environment variables in Railway dashboard
# HTTPS: Automatic SSL with custom domains
```

### Render

1. Connect your GitHub repository
2. Create a new Web Service
3. Set environment variables in dashboard
4. Deploy automatically on push
5. **HTTPS:** Free automatic SSL

### DigitalOcean App Platform

1. Create new app from GitHub
2. Configure environment variables
3. Deploy
4. **HTTPS:** Automatic SSL with custom domains

---

## 🔐 Security Best Practices

### 1. Environment Variables

✅ **Never commit `.env` to Git**
- Already in `.gitignore`
- Use `.env.example` as template only

### 2. Strong Passwords

```bash
# Generate strong SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate database password (32 chars)
openssl rand -base64 32
```

### 3. CORS Configuration

```env
# Production - specific domains only
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Development - all origins allowed automatically
CORS_ORIGINS=http://localhost:3000
```

### 4. Database Security

- Use strong passwords
- Enable firewall (allow only backend container)
- Regular backups
- Use connection pooling

### 5. SSL/TLS

- Use Let's Encrypt or commercial certificates
- Enable HSTS headers (already in nginx.conf)
- Use TLS 1.2+ only (already configured)
- Monitor certificate expiry

---

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Backend health
curl https://yourdomain.com/health

# Database connectivity
docker-compose exec backend python -c "from app.database import engine; print('DB OK' if engine else 'DB ERROR')"
```

### Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f celery_worker
```

### Backups

```bash
# MySQL backup
docker-compose exec mysql mysqldump -u root -p auratask > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T mysql mysql -u root -p auratask < backup_20260124.sql
```

---

## 🔧 Troubleshooting

### SSL Certificate Issues

**Problem:** "Certificate not valid"
```bash
# Check certificate
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Verify domain matches
# Check certificate expiry date
```

**Problem:** "Mixed content warnings"
- Ensure all API calls use `https://` in frontend
- Check CORS_ORIGINS uses `https://`

### CORS Errors

**Problem:** "Access blocked by CORS policy"
```bash
# Check CORS_ORIGINS in .env
grep CORS_ORIGINS backend/.env

# Restart backend
docker-compose restart backend
```

### Database Connection

**Problem:** "Can't connect to MySQL"
```bash
# Check MySQL is running
docker-compose ps mysql

# Check credentials
docker-compose exec backend python -c "from app.config import settings; print(settings.DB_HOST, settings.DB_USER)"
```

### Celery Worker Issues

**Problem:** "Notifications not sending"
```bash
# Check Celery worker logs
docker-compose logs celery_worker

# Check Celery beat (scheduler)
docker-compose logs celery_beat

# Restart workers
docker-compose restart celery_worker celery_beat
```

---

## 🎯 Post-Deployment Verification

After deployment, verify all features work:

- [ ] ✅ HTTPS loads without warnings
- [ ] ✅ Login/registration works
- [ ] ✅ Task creation with NLP works
- [ ] ✅ WebSocket live updates work
- [ ] ✅ Email notifications send
- [ ] ✅ Telegram notifications work (if configured)
- [ ] ✅ Discord notifications work (if configured)
- [ ] ✅ Health endpoint returns correct data
- [ ] ✅ API documentation accessible at `/docs`

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review this guide
- Check GitHub Issues

---

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs for errors
docker-compose logs -f
```

### Certificate Renewal

Let's Encrypt certificates expire every 90 days:

```bash
# Manual renewal
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# Restart Nginx
docker-compose restart nginx
```

---

**🎉 Congratulations!** Your AuraTask instance is now deployed securely with HTTPS in production!
