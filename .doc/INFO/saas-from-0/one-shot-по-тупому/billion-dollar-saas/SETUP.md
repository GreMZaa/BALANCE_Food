# Setup Guide for InterviewPro

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Database Setup

#### Option A: Local PostgreSQL

1. Install PostgreSQL if you haven't already
2. Create a database:
```sql
CREATE DATABASE interviewpro;
```

3. Update `.env`:
```
DATABASE_URL="postgresql://user:password@localhost:5432/interviewpro"
```

#### Option B: Use a Cloud Database (Recommended)

- **Supabase** (Free tier available): https://supabase.com
- **Neon** (Free tier available): https://neon.tech
- **Railway** (Free tier available): https://railway.app

Copy the connection string to your `.env` file.

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL="your-postgresql-connection-string"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="generate-a-random-secret-here"

# Google OAuth (Optional but recommended)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Stripe (Required for payments)
STRIPE_SECRET_KEY="sk_test_your-stripe-secret-key"
STRIPE_PUBLISHABLE_KEY="pk_test_your-stripe-publishable-key"
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_your-stripe-publishable-key"
STRIPE_WEBHOOK_SECRET="whsec_your-webhook-secret"

# Stripe Price IDs (Create these in Stripe Dashboard)
STRIPE_PRO_PRICE_ID="price_xxxxx"
STRIPE_PREMIUM_PRICE_ID="price_xxxxx"

# Email (Optional - for email auth)
EMAIL_SERVER_HOST="smtp.gmail.com"
EMAIL_SERVER_PORT=587
EMAIL_SERVER_USER="your-email@gmail.com"
EMAIL_SERVER_PASSWORD="your-app-password"
EMAIL_FROM="noreply@interviewpro.com"
```

### 4. Generate NextAuth Secret

```bash
openssl rand -base64 32
```

Use the output as your `NEXTAUTH_SECRET`.

### 5. Set Up Google OAuth (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
6. Copy Client ID and Client Secret to `.env`

### 6. Set Up Stripe

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Dashboard
3. Create products and prices:
   - **Pro Plan**: $19/month recurring
   - **Premium Plan**: $49/month recurring
4. Copy the Price IDs to your `.env` file
5. Set up webhook endpoint:
   - URL: `https://yourdomain.com/api/webhooks/stripe`
   - Events to listen: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy webhook secret to `.env`

### 7. Initialize Database

```bash
# Push schema to database
npx prisma db push

# Seed with sample questions
npm run db:seed
```

### 8. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Production Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Add environment variables in Vercel dashboard
4. Deploy!

### Other Platforms

The app can be deployed to any platform that supports Next.js:
- Railway
- Render
- AWS Amplify
- DigitalOcean App Platform

## Troubleshooting

### Database Connection Issues

- Verify your `DATABASE_URL` is correct
- Check if your database is accessible
- For cloud databases, check firewall/network settings

### Authentication Not Working

- Verify `NEXTAUTH_SECRET` is set
- Check `NEXTAUTH_URL` matches your domain
- For Google OAuth, verify redirect URIs are correct

### Stripe Payments Not Working

- Verify all Stripe keys are set correctly
- Check webhook endpoint is configured
- Use Stripe test mode for development
- Verify webhook secret matches

## Next Steps

1. Customize the branding and colors
2. Add more interview questions
3. Integrate real AI feedback (OpenAI API)
4. Add more features based on user feedback
5. Set up analytics (Google Analytics, Mixpanel, etc.)
6. Configure email notifications
7. Add social sharing features

## Support

For issues or questions, check the README.md or open an issue on GitHub.

