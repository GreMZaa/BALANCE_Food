import { NextResponse } from "next/server"
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { prisma } from "@/lib/prisma"

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions)
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { questionId, answer } = await request.json()

    if (!questionId || !answer) {
      return NextResponse.json({ error: "Missing questionId or answer" }, { status: 400 })
    }

    // Create or update practice session
    const practiceSession = await prisma.practiceSession.create({
      data: {
        userId: session.user.id,
        type: "PRACTICE",
        questions: {
          create: {
            questionId,
            userAnswer: answer,
            timeSpent: 0, // Could be calculated on client side
          },
        },
      },
    })

    // Update progress
    const progress = await prisma.progress.upsert({
      where: { userId: session.user.id },
      create: {
        userId: session.user.id,
        totalQuestions: 1,
        correctAnswers: 0, // Would need actual validation
        lastPracticeAt: new Date(),
      },
      update: {
        totalQuestions: { increment: 1 },
        lastPracticeAt: new Date(),
      },
    })

    return NextResponse.json({ success: true, sessionId: practiceSession.id })
  } catch (error) {
    console.error("Error submitting practice:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

