import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('Creating test user...')

  // Проверяем, существует ли пользователь
  let user = await prisma.user.findUnique({
    where: { email: 'test@test.com' }
  })

  if (user) {
    console.log('Test user already exists!')
    console.log('Email: test@test.com')
    console.log('Password: test123')
    return
  }

  // Создаём пользователя
  user = await prisma.user.create({
    data: {
      email: 'test@test.com',
      name: 'Test User',
      emailVerified: new Date(),
    }
  })

  // Создаём подписку FREE
  await prisma.subscription.create({
    data: {
      userId: user.id,
      status: 'FREE',
    }
  })

  // Создаём прогресс
  await prisma.progress.create({
    data: {
      userId: user.id,
    }
  })

  console.log('✅ Test user created successfully!')
  console.log('Email: test@test.com')
  console.log('Password: test123')
  console.log('You can now login at http://localhost:3000/auth/signin')
}

main()
  .catch((e) => {
    console.error('Error creating test user:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

