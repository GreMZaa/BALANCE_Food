import { redirect } from "next/navigation"
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { prisma } from "@/lib/prisma"
import { getSubscriptionStatus, getDailyQuestionLimit } from "@/lib/subscription"
import { PracticeClient } from "./practice-client"

export default async function PracticePage() {
  const session = await getServerSession(authOptions)
  
  if (!session?.user?.id) {
    redirect("/auth/signin")
  }

  const userId = session.user.id
  
  // Проверяем, настроена ли БД
  let subscriptionStatus = "FREE"
  let dailyLimit = 5
  let todayQuestionCount = 0
  let question = null

  if (process.env.DATABASE_URL && prisma) {
    try {
      subscriptionStatus = await getSubscriptionStatus(userId)
      dailyLimit = await getDailyQuestionLimit(userId)

      // Get today's practice count
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      
      const todaySessions = await prisma.practiceSession.findMany({
        where: {
          userId,
          createdAt: { gte: today },
        },
        include: {
          questions: true,
        },
      })

      todayQuestionCount = todaySessions.reduce((sum, session) => sum + session.questions.length, 0)

      // Get a random question
      const questionCount = await prisma.question.count()
      const skip = Math.floor(Math.random() * questionCount)
      question = await prisma.question.findFirst({
        skip,
      })
    } catch (error) {
      console.error("Database error:", error)
    }
  }
  
  if (!question) {
    // Mock вопрос для разработки без БД
    // Mock вопрос для разработки без БД
    question = {
      id: "mock-1",
      title: "Two Sum",
      description: "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
      category: "ALGORITHMS",
      difficulty: "EASY",
      company: "Google",
      tags: ["array", "hash-table"],
      hints: ["Use a hash map", "Iterate through the array"],
      solution: "function twoSum(nums, target) { const map = new Map(); for (let i = 0; i < nums.length; i++) { const complement = target - nums[i]; if (map.has(complement)) { return [map.get(complement), i]; } map.set(nums[i], i); } return []; }",
    }
  }

  return (
    <PracticeClient
      question={question}
      subscriptionStatus={subscriptionStatus}
      dailyLimit={dailyLimit}
      todayQuestionCount={todayQuestionCount}
    />
  )
}

