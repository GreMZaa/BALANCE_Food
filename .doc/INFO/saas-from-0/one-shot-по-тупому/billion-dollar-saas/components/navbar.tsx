"use client"

import Link from "next/link"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Code } from "lucide-react"
import { useEffect, useState } from "react"

export function Navbar() {
  const { data: session, status } = useSession()
  const [subscriptionStatus, setSubscriptionStatus] = useState<string>("FREE")

  useEffect(() => {
    if (session?.user?.id) {
      fetch("/api/user/subscription")
        .then((res) => res.json())
        .then((data) => {
          if (data.status) {
            setSubscriptionStatus(data.status)
          }
        })
        .catch(() => {})
    }
  }, [session])

  return (
    <nav className="border-b">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-2">
          <Code className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">InterviewPro</span>
        </Link>
        <div className="flex items-center gap-4">
          {status === "loading" ? (
            <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
          ) : session ? (
            <>
              <Link href="/dashboard">
                <Button variant="ghost">Dashboard</Button>
              </Link>
              <Link href="/practice">
                <Button variant="ghost">Practice</Button>
              </Link>
              <Badge variant={subscriptionStatus === "FREE" ? "secondary" : "default"}>
                {subscriptionStatus}
              </Badge>
              {subscriptionStatus === "FREE" && (
                <Link href="/pricing">
                  <Button>Upgrade</Button>
                </Link>
              )}
              <Button variant="ghost" onClick={() => signOut()}>
                Sign Out
              </Button>
            </>
          ) : (
            <>
              <Link href="/auth/signin">
                <Button variant="ghost">Sign In</Button>
              </Link>
              <Link href="/auth/signin">
                <Button>Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

