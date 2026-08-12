import { redirect } from "next/navigation"
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { canAccessFeature } from "@/lib/subscription"
import { MockInterviewClient } from "./mock-interview-client"

export default async function MockInterviewPage() {
  const session = await getServerSession(authOptions)
  
  if (!session?.user?.id) {
    redirect("/auth/signin")
  }

  const userId = session.user.id
  const hasAccess = await canAccessFeature(userId, "mock_interviews")

  if (!hasAccess) {
    redirect("/pricing?upgrade=mock-interview")
  }

  return <MockInterviewClient />
}

