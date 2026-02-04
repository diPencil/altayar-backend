# AltayarVIP Backend - Production Deployment Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Google Cloud Setup](#google-cloud-setup)
4. [Cloud SQL PostgreSQL](#cloud-sql-postgresql)
5. [Secret Manager Setup](#secret-manager-setup)
6. [Cloud Run Deployment](#cloud-run-deployment)
7. [Domain Mapping & HTTPS](#domain-mapping--https)
8. [Fawaterk Webhook Configuration](#fawaterk-webhook-configuration)
9. [Production Testing Checklist](#production-testing-checklist)
10. [Monitoring & Logging](#monitoring--logging)
11. [API Reference](#api-reference)

---

## Overview

**AltayarVIP** is a tourism platform backend built with:
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL (Cloud SQL)
- **Hosting:** Google Cloud Run
- **Payments:** Fawaterk Payment Gateway

### Production URLs
| Service | URL |
|---------|-----|
| **API Base** | `https://api.altayarvip.com` |
| **Health Check** | `https://api.altayarvip.com/health` |
| **Webhook** | `https://api.altayarvip.com/api/payments/fawaterk/webhook` |

---

## Prerequisites

### Required Tools
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Authenticate
gcloud auth login
gcloud auth application-default login
```

### Enable Required APIs
```bash
PROJECT_ID="your-project-id"

gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    containerregistry.googleapis.com \
    --project=$PROJECT_ID
```

---

## Google Cloud Setup

### Step 1: Set Project Variables
```bash
export PROJECT_ID="altayarvip-prod"
export REGION="me-central1"  # Middle East (Qatar) - closest to Egypt
export SERVICE_NAME="altayarvip-backend"
export DB_INSTANCE="altayarvip-db"

gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

---

## Cloud SQL PostgreSQL

### Step 2: Create Cloud SQL Instance
```bash
# Create PostgreSQL 15 instance
gcloud sql instances create $DB_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --availability-type=zonal \
    --root-password="GENERATE_SECURE_PASSWORD_HERE"

# Note the connection name
gcloud sql instances describe $DB_INSTANCE --format="value(connectionName)"
# Output: PROJECT_ID:REGION:altayarvip-db
```

### Step 3: Create Database and User
```bash
# Create database
gcloud sql databases create altayarvip --instance=$DB_INSTANCE

# Create application user
gcloud sql users create altayarvip_user \
    --instance=$DB_INSTANCE \
    --password="GENERATE_SECURE_PASSWORD_HERE"

# Grant permissions (connect via Cloud SQL Proxy or Cloud Shell)
# GRANT ALL PRIVILEGES ON DATABASE altayarvip TO altayarvip_user;
```

### Step 4: Get Connection String
```
# Format for Cloud Run (Unix socket):
postgresql+psycopg2://altayarvip_user:PASSWORD@/altayarvip?host=/cloudsql/PROJECT_ID:REGION:altayarvip-db

# Example:
postgresql+psycopg2://altayarvip_user:SecurePass123@/altayarvip?host=/cloudsql/altayarvip-prod:me-central1:altayarvip-db
```

---

## Secret Manager Setup

### Step 5: Create Secrets
```bash
# Database URL
echo -n "postgresql+psycopg2://altayarvip_user:YOUR_PASSWORD@/altayarvip?host=/cloudsql/$PROJECT_ID:$REGION:$DB_INSTANCE" | \
    gcloud secrets create altayarvip-database-url --data-file=-

# JWT Secret Key (generate secure 64-char hex)
openssl rand -hex 32 | \
    gcloud secrets create altayarvip-jwt-secret --data-file=-

# Fawaterk API Key
echo -n "YOUR_FAWATERK_API_KEY" | \
    gcloud secrets create altayarvip-fawaterk-api-key --data-file=-

# Fawaterk Vendor Key
echo -n "YOUR_FAWATERK_VENDOR_KEY" | \
    gcloud secrets create altayarvip-fawaterk-vendor-key --data-file=-
```

### Step 6: Grant Cloud Run Access to Secrets
```bash
# Get Cloud Run service account
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Or use default Cloud Run service account
SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default" --format="value(email)")

# Grant access to each secret
for SECRET in altayarvip-database-url altayarvip-jwt-secret altayarvip-fawaterk-api-key altayarvip-fawaterk-vendor-key; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
done
```

---

## Cloud Run Deployment

### Step 7: Build and Push Docker Image
```bash
# Build locally first (optional test)
docker build -t altayarvip-backend .

# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Or use Cloud Build (recommended for CI/CD)
gcloud builds submit --config=cloudbuild.yaml
```

### Step 8: Deploy to Cloud Run
```bash
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 80 \
    --set-cloudsql-instances $PROJECT_ID:$REGION:$DB_INSTANCE \
    --update-secrets "DATABASE_URL=altayarvip-database-url:latest" \
    --update-secrets "JWT_SECRET_KEY=altayarvip-jwt-secret:latest" \
    --update-secrets "FAWATERK_API_KEY=altayarvip-fawaterk-api-key:latest" \
    --update-secrets "FAWATERK_VENDOR_KEY=altayarvip-fawaterk-vendor-key:latest" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "DEBUG=false" \
    --set-env-vars "APP_BASE_URL=https://api.altayarvip.com" \
    --set-env-vars "FAWATERK_BASE_URL=https://app.fawaterk.com/api/v2" \
    --set-env-vars "FAWATERK_PROVIDER_KEY=FAWATERAK.19700" \
    --set-env-vars "FAWATERK_TEST_MODE=false" \
    --set-env-vars "CORS_ORIGINS=https://altayarvip.com,https://app.altayarvip.com"
```

### Step 9: Verify Deployment
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --format="value(status.url)")
echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl -s "$SERVICE_URL/health"
# Expected: {"status":"healthy"}

# Test API root
curl -s "$SERVICE_URL/"
# Expected: {"message":"AltayarVIP API","version":"1.0.0","status":"running"}
```

---

## Domain Mapping & HTTPS

### Step 10: Verify Domain Ownership
```bash
# Add domain to Cloud Run
gcloud beta run domain-mappings create \
    --service $SERVICE_NAME \
    --domain api.altayarvip.com \
    --region $REGION
```

### Step 11: Configure DNS
Add these DNS records at your domain registrar:

| Type | Name | Value |
|------|------|-------|
| **A** | api | `216.239.32.21` |
| **A** | api | `216.239.34.21` |
| **A** | api | `216.239.36.21` |
| **A** | api | `216.239.38.21` |
| **AAAA** | api | `2001:4860:4802:32::15` |
| **AAAA** | api | `2001:4860:4802:34::15` |
| **AAAA** | api | `2001:4860:4802:36::15` |
| **AAAA** | api | `2001:4860:4802:38::15` |

**OR** use CNAME (simpler):
| Type | Name | Value |
|------|------|-------|
| **CNAME** | api | `ghs.googlehosted.com.` |

### Step 12: Verify HTTPS
```bash
# Wait for SSL provisioning (up to 24 hours, usually ~15 mins)
gcloud beta run domain-mappings describe \
    --domain api.altayarvip.com \
    --region $REGION

# Test HTTPS
curl -s https://api.altayarvip.com/health
```

---

## Fawaterk Webhook Configuration

### Final Webhook URL
```
https://api.altayarvip.com/api/payments/fawaterk/webhook
```

### Configure in Fawaterk Dashboard
1. Login to [Fawaterk Dashboard](https://app.fawaterk.com)
2. Go to **Settings** → **Webhooks**
3. Add webhook URL: `https://api.altayarvip.com/api/payments/fawaterk/webhook`
4. Enable events: `paid`, `failed`, `expired`

### Webhook Payload Format
```json
{
    "invoice_id": "12345",
    "InvoiceKey": "abc123",
    "PaymentMethod": "card",
    "invoice_status": "paid",
    "amount_cents": "100000",
    "hashKey": "hmac_sha256_signature"
}
```

### Hash Verification
```python
# PAID/FAILED events:
query_param = f"InvoiceId={invoice_id}&InvoiceKey={invoice_key}&PaymentMethod={payment_method}"
expected_hash = hmac.new(VENDOR_KEY, query_param.encode(), sha256).hexdigest()

# EXPIRED events:
query_param = f"referenceId={reference_id}&PaymentMethod={payment_method}"
expected_hash = hmac.new(VENDOR_KEY, query_param.encode(), sha256).hexdigest()
```

---

## Production Testing Checklist

### ✅ Pre-Deployment Tests

| # | Test | Command | Expected |
|---|------|---------|----------|
| 1 | Health Check | `curl https://api.altayarvip.com/health` | `{"status":"healthy"}` |
| 2 | Database Connection | `curl https://api.altayarvip.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"wrong"}'` | `{"detail":"Invalid email or password"}` (not connection error) |

### ✅ Authentication Tests

| # | Test | Command |
|---|------|---------|
| 3 | Register | `curl -X POST https://api.altayarvip.com/api/auth/register -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"Test123456","first_name":"Test","last_name":"User"}'` |
| 4 | Login | `curl -X POST https://api.altayarvip.com/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"Test123456"}'` |
| 5 | Get Profile | `curl https://api.altayarvip.com/api/auth/me -H "Authorization: Bearer TOKEN"` |

### ✅ Payment Flow Tests

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 6 | **Initiate Payment** | `POST /api/orders/{id}/pay` | Returns `payment_url` |
| 7 | **Webhook: PAID** | POST webhook with valid hash | Order status → PAID |
| 8 | **Webhook: FAILED** | POST webhook with failed status | Order status unchanged, payment FAILED |
| 9 | **Webhook: EXPIRED** | POST webhook with expired status | Payment EXPIRED |
| 10 | **Idempotency** | Send same webhook twice | Second returns "already_processed" |

### ✅ Payment Test Commands

```bash
# Set variables
API_URL="https://api.altayarvip.com"
TOKEN="your_jwt_token"
ORDER_ID="your_order_id"

# 6. Initiate Payment
curl -X POST "$API_URL/api/orders/$ORDER_ID/pay" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"payment_method_id": 1}'

# 7. Simulate PAID Webhook (use real hash from Fawaterk)
curl -X POST "$API_URL/api/payments/fawaterk/webhook" \
    -H "Content-Type: application/json" \
    -d '{
        "invoice_id": "12345",
        "InvoiceKey": "key123",
        "PaymentMethod": "card",
        "invoice_status": "paid",
        "hashKey": "computed_hmac_hash"
    }'

# 8. Check Order Status
curl "$API_URL/api/orders/$ORDER_ID" \
    -H "Authorization: Bearer $TOKEN"

# 9. Check Webhook Logs
curl "$API_URL/api/payments/webhook-logs" \
    -H "Authorization: Bearer $TOKEN"
```

### ✅ Invoice Tests

| # | Test | Command |
|---|------|---------|
| 11 | Get Invoice Data | `curl https://api.altayarvip.com/api/orders/{id}/invoice -H "Authorization: Bearer TOKEN"` |
| 12 | Download PDF | `curl -o invoice.pdf https://api.altayarvip.com/api/orders/{id}/invoice/download -H "Authorization: Bearer TOKEN"` |

### ✅ Full E2E Test Flow

```bash
#!/bin/bash
API_URL="https://api.altayarvip.com"

# 1. Register Admin (one-time via DB)
# 2. Login
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@altayarvip.com","password":"AdminPass123"}' | jq -r '.access_token')

# 3. Create Order
ORDER=$(curl -s -X POST "$API_URL/api/orders" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "customer_id",
        "order_type": "MANUAL_INVOICE",
        "items": [{"description_ar":"خدمة","description_en":"Service","quantity":1,"unit_price":100}]
    }')
ORDER_ID=$(echo $ORDER | jq -r '.id')

# 4. Issue Order
curl -X POST "$API_URL/api/orders/$ORDER_ID/issue" \
    -H "Authorization: Bearer $TOKEN"

# 5. Initiate Payment
PAYMENT=$(curl -s -X POST "$API_URL/api/orders/$ORDER_ID/pay" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"payment_method_id": 1}')
echo "Payment URL: $(echo $PAYMENT | jq -r '.payment_url')"

# 6. (Fawaterk calls webhook after payment)

# 7. Verify Order Status
curl -s "$API_URL/api/orders/$ORDER_ID" \
    -H "Authorization: Bearer $TOKEN" | jq '.payment_status'

# 8. Download Invoice
curl -o "invoice_$ORDER_ID.pdf" "$API_URL/api/orders/$ORDER_ID/invoice/download" \
    -H "Authorization: Bearer $TOKEN"
```

---

## Monitoring & Logging

### Cloud Run Logs
```bash
# View logs
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100

# Stream logs
gcloud run services logs tail $SERVICE_NAME --region $REGION
```

### Cloud SQL Monitoring
```bash
# View database metrics
gcloud sql instances describe $DB_INSTANCE --format="yaml(settings.databaseFlags)"
```

### Set Up Alerts
```bash
# Create alert policy for 5xx errors
gcloud alpha monitoring policies create \
    --notification-channels="your-channel-id" \
    --display-name="Cloud Run 5xx Errors" \
    --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"'
```

---

## API Reference

### Base URL
```
https://api.altayarvip.com
```

### Endpoints Summary

| Module | Endpoints |
|--------|-----------|
| **Auth** | `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me` |
| **Orders** | `/api/orders`, `/api/orders/me`, `/api/orders/{id}`, `/api/orders/{id}/pay`, `/api/orders/{id}/issue` |
| **Invoices** | `/api/orders/{id}/invoice`, `/api/orders/{id}/invoice/download` |
| **Payments** | `/api/payments/fawaterk/webhook`, `/api/payments/status/{id}`, `/api/payments/webhook-logs` |
| **Bookings** | `/api/bookings`, `/api/bookings/me`, `/api/bookings/{id}`, `/api/bookings/{id}/status` |
| **Wallet** | `/api/wallet/me`, `/api/wallet/me/balance`, `/api/wallet/me/transactions` |
| **Points** | `/api/points/me`, `/api/points/me/transactions`, `/api/points/me/redeem` |
| **Cashback** | `/api/cashback/me`, `/api/cashback/me/summary` |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `Connection refused` to DB | Check Cloud SQL instance is running, IAM permissions |
| `Invalid hash` on webhook | Verify FAWATERK_VENDOR_KEY is correct |
| SSL certificate pending | Wait up to 24 hours, verify DNS records |
| Cold start slow | Increase `--min-instances` to 1+ |

### Useful Commands
```bash
# Check service status
gcloud run services describe $SERVICE_NAME --region $REGION

# Check Cloud SQL status
gcloud sql instances describe $DB_INSTANCE

# List secrets
gcloud secrets list

# Update secret
echo -n "new_value" | gcloud secrets versions add SECRET_NAME --data-file=-

# Force new deployment
gcloud run services update $SERVICE_NAME --region $REGION --no-traffic
```

---

## Security Checklist

- [ ] All secrets in Secret Manager (not in code)
- [ ] HTTPS only (Cloud Run default)
- [ ] Database password is strong (32+ chars)
- [ ] JWT secret is 64-char hex
- [ ] CORS restricted to known origins
- [ ] Webhook hash verification enabled
- [ ] Rate limiting configured (Cloud Armor optional)
- [ ] Audit logging enabled

---

## Cost Estimation (Monthly)

| Service | Specification | Est. Cost |
|---------|---------------|-----------|
| Cloud Run | 1 vCPU, 1GB RAM, min 1 instance | ~$25-50 |
| Cloud SQL | db-f1-micro, 10GB SSD | ~$10-15 |
| Secret Manager | 4 secrets, low access | ~$0.50 |
| Container Registry | ~500MB images | ~$1 |
| **Total** | | **~$35-70/month** |

---

**Last Updated:** December 2025  
**Version:** 1.0.0  
**Maintainer:** AltayarVIP Team
