# InterviewPro - SaaS Interview Preparation Platform

A comprehensive SaaS platform for technical interview preparation, designed to help developers ace their coding interviews and land their dream jobs.

## Features

- 🎯 **10,000+ Practice Questions** - Curated questions from top tech companies
- 🤖 **AI-Powered Feedback** - Get instant, detailed feedback on your solutions
- 🎭 **Mock Interviews** - Simulate real interview conditions
- 📊 **Progress Tracking** - Monitor your improvement with detailed analytics
- 🏢 **Company-Specific Prep** - Focus on questions from your target companies
- 💰 **Flexible Pricing** - Free tier + Pro ($19/mo) + Premium ($49/mo)

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Authentication**: NextAuth.js
- **Payments**: Stripe
- **Styling**: Tailwind CSS + shadcn/ui
- **Deployment**: Vercel-ready

## Getting Started

### Prerequisites

- Node.js 18+ 
- PostgreSQL database
- Stripe account (for payments)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd billion-dollar-saas
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Fill in your environment variables:
```
DATABASE_URL="postgresql://user:password@localhost:5432/interviewpro"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key"
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
STRIPE_SECRET_KEY="your-stripe-secret-key"
STRIPE_PUBLISHABLE_KEY="your-stripe-publishable-key"
```

4. Set up the database:
```bash
npx prisma db push
npx prisma db seed
```

5. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   ├── auth/              # Authentication pages
│   ├── dashboard/         # User dashboard
│   ├── practice/          # Practice interface
│   └── pricing/           # Pricing page
├── components/            # React components
│   └── ui/               # shadcn/ui components
├── lib/                   # Utility functions
├── prisma/                # Database schema and migrations
└── public/                # Static assets
```

## Monetization Strategy

### Free Tier
- 5 questions per day
- Basic solutions
- Progress tracking

### Pro Tier ($19/month)
- Unlimited questions
- AI-powered feedback
- Mock interviews
- Company-specific prep
- Detailed solutions

### Premium Tier ($49/month)
- Everything in Pro
- 1-on-1 coaching sessions
- Resume review
- Priority support
- Custom study plans

## Revenue Projections

To reach $20,000/month:
- **Pro Plan**: ~1,053 subscribers × $19 = $20,007/month
- **Premium Plan**: ~408 subscribers × $49 = $19,992/month
- **Mixed**: ~800 Pro + ~100 Premium = $20,700/month

## Development

### Database Commands

```bash
# Push schema changes
npm run db:push

# Open Prisma Studio
npm run db:studio

# Seed database
npm run db:seed
```

### Building for Production

```bash
npm run build
npm start
```

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT

## Support

For questions or support, please open an issue or contact the maintainer.

---

Built with ❤️ to help developers land their dream jobs.

