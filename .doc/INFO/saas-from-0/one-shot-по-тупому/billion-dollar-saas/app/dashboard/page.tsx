import { redirect } from "next/navigation"
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { prisma } from "@/lib/prisma"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { Code, TrendingUp, Clock, Target, Zap, ArrowRight } from "lucide-react"
import { formatTime } from "@/lib/utils"
import { getSubscriptionStatus } from "@/lib/subscription"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  
  if (!session?.user?.id) {
    redirect("/auth/signin")
  }

  const userId = session.user.id
  
  // Проверяем, настроена ли БД
  let subscriptionStatus = "FREE"
  let progress = null
  let recentSessions: any[] = []

  if (process.env.DATABASE_URL && prisma) {
    try {
      subscriptionStatus = await getSubscriptionStatus(userId)
      progress = await prisma.progress.findUnique({
        where: { userId },
      })
      recentSessions = await prisma.practiceSession.findMany({
        where: { userId },
        orderBy: { createdAt: "desc" },
        take: 5,
        include: {
          questions: {
            include: {
              question: true,
            },
          },
        },
      })
    } catch (error) {
      console.error("Database error:", error)
      // Используем значения по умолчанию
    }
  }

  const accuracy = progress && progress.totalQuestions > 0
    ? Math.round((progress.correctAnswers / progress.totalQuestions) * 100)
    : 0

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <Code className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">InterviewPro</span>
          </Link>
          <div className="flex items-center gap-4">
            <Badge variant={subscriptionStatus === "FREE" ? "secondary" : "default"}>
              {subscriptionStatus}
            </Badge>
            <Link href="/pricing">
              <Button variant="outline">Upgrade</Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back! Here's your progress overview.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Questions</CardTitle>
              <Code className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{progress?.totalQuestions || 0}</div>
              <p className="text-xs text-muted-foreground">Questions practiced</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{accuracy}%</div>
              <Progress value={accuracy} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Time Spent</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {progress?.totalTimeSpent ? formatTime(progress.totalTimeSpent) : "0s"}
              </div>
              <p className="text-xs text-muted-foreground">Total practice time</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Streak</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{progress?.streak || 0}</div>
              <p className="text-xs text-muted-foreground">Day streak</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Start Practicing</CardTitle>
              <CardDescription>Practice coding questions by category or difficulty</CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/practice">
                <Button className="w-full">
                  Practice Now <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Mock Interview</CardTitle>
              <CardDescription>Simulate a real interview experience</CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/mock-interview">
                <Button className="w-full" variant="outline">
                  Start Mock Interview <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Recent Sessions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Practice Sessions</CardTitle>
            <CardDescription>Your latest practice activities</CardDescription>
          </CardHeader>
          <CardContent>
            {recentSessions.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No practice sessions yet. Start practicing to see your progress here!
              </p>
            ) : (
              <div className="space-y-4">
                {recentSessions.map((session) => (
                  <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <p className="font-medium">{session.type.replace("_", " ")}</p>
                      <p className="text-sm text-muted-foreground">
                        {session.questions.length} questions • {new Date(session.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                    {session.score !== null && (
                      <Badge variant={session.score >= 70 ? "default" : "secondary"}>
                        {session.score}%
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

