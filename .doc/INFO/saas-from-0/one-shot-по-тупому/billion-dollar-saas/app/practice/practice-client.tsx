"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import Link from "next/link"
import { ArrowLeft, Lightbulb, CheckCircle2, XCircle, Code } from "lucide-react"
import { useRouter } from "next/navigation"

interface Question {
  id: string
  title: string
  description: string
  category: string
  difficulty: string
  company: string | null
  tags: string[]
  hints: string[]
  solution: string | null
}

interface PracticeClientProps {
  question: Question | null
  subscriptionStatus: string
  dailyLimit: number
  todayQuestionCount: number
}

export function PracticeClient({ question, subscriptionStatus, dailyLimit, todayQuestionCount }: PracticeClientProps) {
  const router = useRouter()
  const [answer, setAnswer] = useState("")
  const [showHints, setShowHints] = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  const canPractice = subscriptionStatus !== "FREE" || todayQuestionCount < dailyLimit
  const remainingQuestions = dailyLimit - todayQuestionCount

  const handleSubmit = async () => {
    if (!question || !answer.trim()) return

    // Simulate AI feedback
    const simulatedFeedback = `Your solution looks good! Here are some points to consider:
    
1. **Time Complexity**: Make sure your solution is optimal. Consider if you can improve the time complexity.
2. **Edge Cases**: Did you handle edge cases like empty inputs, single elements, etc.?
3. **Code Quality**: Is your code readable and well-structured?
4. **Space Complexity**: Consider if you can optimize space usage.

Keep practicing!`

    setFeedback(simulatedFeedback)
    setSubmitted(true)

    // Save to database
    try {
      await fetch("/api/practice/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questionId: question.id,
          answer,
        }),
      })
    } catch (error) {
      console.error("Failed to save practice session:", error)
    }
  }

  const handleNext = () => {
    router.refresh()
    setAnswer("")
    setShowHints(false)
    setShowSolution(false)
    setSubmitted(false)
    setFeedback(null)
  }

  if (!canPractice) {
    return (
      <div className="min-h-screen bg-background">
        <nav className="border-b">
          <div className="container mx-auto px-4 py-4">
            <Link href="/dashboard" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>
          </div>
        </nav>
        <div className="container mx-auto px-4 py-20">
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle>Daily Limit Reached</CardTitle>
              <CardDescription>You've reached your daily limit of {dailyLimit} questions.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4">Upgrade to Pro for unlimited practice questions!</p>
              <Link href="/pricing">
                <Button>Upgrade to Pro</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (!question) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">No questions available. Please check back later.</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          {subscriptionStatus === "FREE" && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {remainingQuestions} questions remaining today
              </span>
              <Progress value={(todayQuestionCount / dailyLimit) * 100} className="w-24" />
            </div>
          )}
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-6 flex items-center gap-2">
          <Badge variant={question.difficulty === "EASY" ? "default" : question.difficulty === "MEDIUM" ? "secondary" : "destructive"}>
            {question.difficulty}
          </Badge>
          <Badge variant="outline">{question.category.replace("_", " ")}</Badge>
          {question.company && (
            <Badge variant="outline">{question.company}</Badge>
          )}
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{question.title}</CardTitle>
            <CardDescription>{question.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Your Solution</label>
                <Textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Write your solution here..."
                  className="min-h-[200px] font-mono"
                  disabled={submitted}
                />
              </div>

              {!submitted && (
                <div className="flex gap-2">
                  <Button onClick={handleSubmit} disabled={!answer.trim()}>
                    Submit Solution
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowHints(!showHints)}
                  >
                    <Lightbulb className="mr-2 h-4 w-4" />
                    {showHints ? "Hide" : "Show"} Hints
                  </Button>
                  {subscriptionStatus !== "FREE" && (
                    <Button
                      variant="outline"
                      onClick={() => setShowSolution(!showSolution)}
                    >
                      <Code className="mr-2 h-4 w-4" />
                      {showSolution ? "Hide" : "Show"} Solution
                    </Button>
                  )}
                </div>
              )}

              {submitted && (
                <div className="flex gap-2">
                  <Button onClick={handleNext}>
                    Next Question
                  </Button>
                  {subscriptionStatus !== "FREE" && (
                    <Button
                      variant="outline"
                      onClick={() => setShowSolution(!showSolution)}
                    >
                      <Code className="mr-2 h-4 w-4" />
                      {showSolution ? "Hide" : "Show"} Solution
                    </Button>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {showHints && question.hints.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Hints</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {question.hints.map((hint, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <Lightbulb className="h-4 w-4 text-yellow-500 mt-1 flex-shrink-0" />
                    <span>{hint}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {feedback && (
          <Card className="mb-6 border-green-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                AI Feedback
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap">{feedback}</div>
            </CardContent>
          </Card>
        )}

        {showSolution && question.solution && (
          <Card>
            <CardHeader>
              <CardTitle>Solution</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                <code>{question.solution}</code>
              </pre>
            </CardContent>
          </Card>
        )}

        {subscriptionStatus === "FREE" && (
          <Card className="mt-6 border-primary">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Unlock unlimited practice</p>
                  <p className="text-sm text-muted-foreground">
                    Get AI feedback, solutions, and unlimited questions
                  </p>
                </div>
                <Link href="/pricing">
                  <Button>Upgrade to Pro</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

