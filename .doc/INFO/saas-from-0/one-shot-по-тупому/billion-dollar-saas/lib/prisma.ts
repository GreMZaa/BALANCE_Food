// Условный импорт Prisma - только если DATABASE_URL установлен
let PrismaClient: any = null
let prismaInstance: any = null

if (process.env.DATABASE_URL) {
  try {
    PrismaClient = require('@prisma/client').PrismaClient
    prismaInstance = new PrismaClient({
      log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
    })
  } catch (error) {
    console.error('Failed to initialize Prisma Client:', error)
    prismaInstance = null
  }
}

// Singleton pattern для development
const globalForPrisma = globalThis as unknown as {
  prisma: any
}

if (process.env.NODE_ENV !== 'production') {
  if (!globalForPrisma.prisma) {
    globalForPrisma.prisma = prismaInstance
  }
  prismaInstance = globalForPrisma.prisma
}

export const prisma = prismaInstance
