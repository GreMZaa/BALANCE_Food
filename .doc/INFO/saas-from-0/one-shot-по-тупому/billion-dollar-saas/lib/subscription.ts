import { prisma } from "./prisma"
import { SubscriptionStatus } from "@prisma/client"

export async function getUserSubscription(userId: string) {
  if (!prisma) return null
  const subscription = await prisma.subscription.findUnique({
    where: { userId },
  })

  return subscription
}

export async function getSubscriptionStatus(userId: string): Promise<SubscriptionStatus> {
  const subscription = await getUserSubscription(userId)
  return subscription?.status || SubscriptionStatus.FREE
}

export async function canAccessFeature(
  userId: string,
  feature: "unlimited_questions" | "ai_feedback" | "mock_interviews" | "premium_support"
): Promise<boolean> {
  const status = await getSubscriptionStatus(userId)

  switch (feature) {
    case "unlimited_questions":
      return status === SubscriptionStatus.PRO || status === SubscriptionStatus.PREMIUM
    case "ai_feedback":
      return status === SubscriptionStatus.PRO || status === SubscriptionStatus.PREMIUM
    case "mock_interviews":
      return status === SubscriptionStatus.PRO || status === SubscriptionStatus.PREMIUM
    case "premium_support":
      return status === SubscriptionStatus.PREMIUM
    default:
      return false
  }
}

export async function getDailyQuestionLimit(userId: string): Promise<number> {
  const status = await getSubscriptionStatus(userId)

  switch (status) {
    case SubscriptionStatus.FREE:
      return 5
    case SubscriptionStatus.PRO:
    case SubscriptionStatus.PREMIUM:
      return Infinity
    default:
      return 5
  }
}

