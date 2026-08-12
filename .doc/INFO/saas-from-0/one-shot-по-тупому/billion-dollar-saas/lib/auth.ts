import { NextAuthOptions } from "next-auth"
import { PrismaAdapter } from "@next-auth/prisma-adapter"
import EmailProvider from "next-auth/providers/email"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"

// Условный импорт Prisma - только если DATABASE_URL установлен
let prisma: any = null
if (process.env.DATABASE_URL) {
  try {
    prisma = require("./prisma").prisma
  } catch (error) {
    console.warn("Prisma not available:", error)
  }
}

export const authOptions: NextAuthOptions = {
  // Для Credentials provider не нужен адаптер, используем JWT
  // Адаптер нужен только для OAuth провайдеров (Google, Email)
  providers: [
    // Credentials provider для разработки (простой вход)
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        try {
          if (!credentials?.email || !credentials?.password) {
            console.log("Missing credentials")
            return null
          }

          // Для разработки: простой тестовый пользователь
          if (credentials.email === "test@test.com" && credentials.password === "test123") {
            console.log("Test user login attempt")
            
            // Всегда используем mock пользователя для тестового аккаунта
            // Это позволяет работать без БД
            console.log("Test user login - using mock user")
            return {
              id: "test-user-id",
              email: credentials.email,
              name: "Test User",
            }
            
            // Если нужна работа с БД, раскомментируйте ниже:
            /*
            const hasDatabase = !!process.env.DATABASE_URL && prisma
            
            if (hasDatabase) {
              try {
                let user = await prisma.user.findUnique({
                  where: { email: credentials.email }
                })

                if (!user) {
                  user = await prisma.user.create({
                    data: {
                      email: credentials.email,
                      name: "Test User",
                      emailVerified: new Date(),
                    }
                  })

                  await prisma.subscription.create({
                    data: {
                      userId: user.id,
                      status: "FREE",
                    }
                  })

                  await prisma.progress.create({
                    data: {
                      userId: user.id,
                    }
                  })
                }

                return {
                  id: user.id,
                  email: user.email,
                  name: user.name,
                }
              } catch (dbError: any) {
                console.error("Database error:", dbError.message)
              }
            }
            */
          }

          // Для других пользователей проверяем через БД (если настроена)
          if (process.env.DATABASE_URL && prisma) {
            try {
              const user = await prisma.user.findUnique({
                where: { email: credentials.email }
              })

              if (!user) {
                console.log("User not found")
                return null
              }

              return {
                id: user.id,
                email: user.email,
                name: user.name,
              }
            } catch (dbError) {
              console.error("Database error:", dbError)
              return null
            }
          }

          return null
        } catch (error) {
          console.error("Error in authorize:", error)
          return null
        }
      }
    }),
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
    EmailProvider({
      server: {
        host: process.env.EMAIL_SERVER_HOST,
        port: process.env.EMAIL_SERVER_PORT,
        auth: {
          user: process.env.EMAIL_SERVER_USER,
          pass: process.env.EMAIL_SERVER_PASSWORD,
        },
      },
      from: process.env.EMAIL_FROM,
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET || "dev-secret-change-in-production",
  pages: {
    signIn: "/auth/signin",
    signOut: "/auth/signout",
  },
  session: {
    strategy: "jwt", // JWT для Credentials provider
  },
  callbacks: {
    async session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub
      }
      return session
    },
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id
      }
      return token
    },
  },
  debug: process.env.NODE_ENV === "development", // Включаем отладку в разработке
}
