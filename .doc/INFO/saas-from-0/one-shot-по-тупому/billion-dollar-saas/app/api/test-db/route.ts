import { NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

export async function GET() {
  try {
    // Простая проверка подключения
    await prisma.$connect()
    const userCount = await prisma.user.count()
    await prisma.$disconnect()
    
    return NextResponse.json({ 
      success: true, 
      message: "Database connection successful",
      userCount 
    })
  } catch (error: any) {
    return NextResponse.json({ 
      success: false, 
      error: error.message,
      details: error.toString()
    }, { status: 500 })
  }
}

