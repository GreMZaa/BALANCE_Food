"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import Link from "next/link"
import { ArrowLeft, Clock, CheckCircle2, XCircle } from "lucide-react"
import { useRouter } from "next/navigation"

export function MockInterviewClient() {
  const router = useRouter()
  const [timeRemaining, setTimeRemaining] = useState(45 * 60) // 45 minutes
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [started, setStarted] = useState(false)
  const [completed, setCompleted] = useState(false)

  const questions = [
    {
      id: 1,
      title: "Two Sum",
      description: "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
      difficulty: "EASY",
      category: "ALGORITHMS",
    },
    {
      id: 2,
      title: "Longest Substring Without Repeating Characters",
      description: "Given a string s, find the length of the longest substring without repeating characters.",
      difficulty: "MEDIUM",
      category: "ALGORITHMS",
    },
    {
      id: 3,
      title: "Merge Intervals",
      description: "Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals.",
      difficulty: "MEDIUM",
      category: "ALGORITHMS",
    },
  ]

  useEffect(() => {
    if (started && !completed && timeRemaining > 0) {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            setCompleted(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [started, completed, timeRemaining])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const handleStart = () => {
    setStarted(true)
  }

  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    } else {
      setCompleted(true)
    }
  }

  if (!started) {
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
              <CardTitle>Mock Interview</CardTitle>
              <CardDescription>
                Simulate a real interview experience with timed questions and comprehensive evaluation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">What to expect:</h3>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>3 coding questions of varying difficulty</li>
                  <li>45 minutes total time</li>
                  <li>Real-time feedback and evaluation</li>
                  <li>Detailed performance report at the end</li>
                </ul>
              </div>
              <Button onClick={handleStart} className="w-full" size="lg">
                Start Mock Interview
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (completed) {
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
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-6 w-6 text-green-500" />
                Interview Completed!
              </CardTitle>
              <CardDescription>Great job completing the mock interview</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Questions Completed:</span>
                  <span className="font-semibold">{currentQuestion + 1} / {questions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Time Remaining:</span>
                  <span className="font-semibold">{formatTime(timeRemaining)}</span>
                </div>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="font-semibold mb-2">Performance Summary:</p>
                <p className="text-sm text-muted-foreground">
                  Your detailed performance report will be available in your dashboard. 
                  Review your solutions and continue practicing to improve!
                </p>
              </div>
              <div className="flex gap-2">
                <Link href="/dashboard" className="flex-1">
                  <Button className="w-full">View Dashboard</Button>
                </Link>
                <Button variant="outline" onClick={() => router.refresh()}>
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const question = questions[currentQuestion]

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span className="font-mono font-semibold">{formatTime(timeRemaining)}</span>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-6">
          <Progress value={((currentQuestion + 1) / questions.length) * 100} className="mb-2" />
          <p className="text-sm text-muted-foreground text-center">
            Question {currentQuestion + 1} of {questions.length}
          </p>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={question.difficulty === "EASY" ? "default" : "secondary"}>
                {question.difficulty}
              </Badge>
              <Badge variant="outline">{question.category.replace("_", " ")}</Badge>
            </div>
            <CardTitle>{question.title}</CardTitle>
            <CardDescription>{question.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 border rounded-lg min-h-[300px]">
                <p className="text-sm text-muted-foreground mb-4">
                  Write your solution in the space below. Think out loud and explain your approach.
                </p>
                <textarea
                  className="w-full h-full min-h-[250px] p-4 font-mono text-sm border rounded bg-background"
                  placeholder="Your solution here..."
                />
              </div>
              <Button onClick={handleNext} className="w-full">
                {currentQuestion < questions.length - 1 ? "Next Question" : "Finish Interview"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

