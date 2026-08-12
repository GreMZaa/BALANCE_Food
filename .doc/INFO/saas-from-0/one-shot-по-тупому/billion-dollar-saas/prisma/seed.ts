import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('Seeding database...')

  // Create sample questions
  const questions = [
    {
      title: "Two Sum",
      description: "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.",
      category: "ALGORITHMS",
      difficulty: "EASY",
      company: "Google",
      tags: ["array", "hash-table"],
      type: "CODING",
      hints: [
        "Use a hash map to store the complement of each number",
        "Iterate through the array and check if the complement exists",
      ],
      solution: `function twoSum(nums: number[], target: number): number[] {
  const map = new Map<number, number>();
  
  for (let i = 0; i < nums.length; i++) {
    const complement = target - nums[i];
    
    if (map.has(complement)) {
      return [map.get(complement)!, i];
    }
    
    map.set(nums[i], i);
  }
  
  return [];
}`,
    },
    {
      title: "Reverse Linked List",
      description: "Given the head of a singly linked list, reverse the list, and return the reversed list.",
      category: "DATA_STRUCTURES",
      difficulty: "EASY",
      company: "Amazon",
      tags: ["linked-list", "recursion"],
      type: "CODING",
      hints: [
        "Use three pointers: prev, current, and next",
        "Iterate through the list and reverse the links",
      ],
      solution: `function reverseList(head: ListNode | null): ListNode | null {
  let prev = null;
  let current = head;
  
  while (current !== null) {
    const next = current.next;
    current.next = prev;
    prev = current;
    current = next;
  }
  
  return prev;
}`,
    },
    {
      title: "Longest Substring Without Repeating Characters",
      description: "Given a string s, find the length of the longest substring without repeating characters.",
      category: "ALGORITHMS",
      difficulty: "MEDIUM",
      company: "Facebook",
      tags: ["string", "sliding-window", "hash-table"],
      type: "CODING",
      hints: [
        "Use a sliding window approach",
        "Keep track of characters in the current window using a set",
        "Expand the window and shrink when duplicates are found",
      ],
      solution: `function lengthOfLongestSubstring(s: string): number {
  const charSet = new Set<string>();
  let left = 0;
  let maxLength = 0;
  
  for (let right = 0; right < s.length; right++) {
    while (charSet.has(s[right])) {
      charSet.delete(s[left]);
      left++;
    }
    
    charSet.add(s[right]);
    maxLength = Math.max(maxLength, right - left + 1);
  }
  
  return maxLength;
}`,
    },
    {
      title: "Design a URL Shortener",
      description: "Design a system like bit.ly that can shorten URLs and redirect to the original URL when accessed.",
      category: "SYSTEM_DESIGN",
      difficulty: "MEDIUM",
      company: "Twitter",
      tags: ["system-design", "distributed-systems"],
      type: "SYSTEM_DESIGN",
      hints: [
        "Consider the scale: billions of URLs",
        "Use base62 encoding for short URLs",
        "Think about database sharding",
        "Consider caching for frequently accessed URLs",
      ],
      solution: `Key Components:
1. URL Shortening Service
   - Generate unique short codes (base62 encoding)
   - Store mapping: short_code -> original_url
   
2. Database Design
   - Use NoSQL for horizontal scaling
   - Shard by short code
   - Index on original URL for deduplication
   
3. Caching Layer
   - Use Redis for hot URLs
   - Cache frequently accessed mappings
   
4. API Design
   - POST /shorten: Create short URL
   - GET /{short_code}: Redirect to original
   
5. Scalability
   - Use consistent hashing for sharding
   - Implement rate limiting
   - Consider CDN for redirects`,
    },
    {
      title: "Tell me about yourself",
      description: "Walk me through your resume and background.",
      category: "BEHAVIORAL",
      difficulty: "EASY",
      company: null,
      tags: ["behavioral", "introduction"],
      type: "BEHAVIORAL",
      hints: [
        "Start with your current role",
        "Highlight relevant experience",
        "Connect your background to the role you're applying for",
        "Keep it concise (2-3 minutes)",
      ],
      solution: `Structure your answer:
1. Current Role (30 seconds)
   - What you do now
   - Key responsibilities
   
2. Relevant Experience (1-2 minutes)
   - Previous roles that relate to the position
   - Key achievements and projects
   
3. Why This Role (30 seconds)
   - What interests you about the position
   - How your experience aligns

Example:
"I'm currently a Senior Software Engineer at [Company], where I've been for the past 3 years. I lead a team of 5 engineers and focus on building scalable backend systems using microservices architecture. Before this, I worked at [Previous Company] where I developed expertise in distributed systems and cloud infrastructure. I'm particularly excited about this role because it combines my passion for system design with the opportunity to work on products that impact millions of users."`,
    },
    {
      title: "Merge Intervals",
      description: "Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.",
      category: "ALGORITHMS",
      difficulty: "MEDIUM",
      company: "Microsoft",
      tags: ["array", "sorting"],
      type: "CODING",
      hints: [
        "Sort intervals by start time",
        "Merge overlapping intervals by comparing with the last merged interval",
      ],
      solution: `function merge(intervals: number[][]): number[][] {
  if (intervals.length === 0) return [];
  
  intervals.sort((a, b) => a[0] - b[0]);
  
  const merged = [intervals[0]];
  
  for (let i = 1; i < intervals.length; i++) {
    const last = merged[merged.length - 1];
    const current = intervals[i];
    
    if (current[0] <= last[1]) {
      last[1] = Math.max(last[1], current[1]);
    } else {
      merged.push(current);
    }
  }
  
  return merged;
}`,
    },
    {
      title: "Binary Tree Maximum Path Sum",
      description: "A path in a binary tree is a sequence of nodes where each pair of adjacent nodes in the sequence has an edge connecting them. A node can only appear in the sequence at most once. Find the maximum path sum.",
      category: "DATA_STRUCTURES",
      difficulty: "HARD",
      company: "Amazon",
      tags: ["binary-tree", "recursion", "dynamic-programming"],
      type: "CODING",
      hints: [
        "Use DFS to traverse the tree",
        "For each node, calculate the maximum path sum that goes through it",
        "Consider both paths: through the node and not through the node",
      ],
      solution: `function maxPathSum(root: TreeNode | null): number {
  let maxSum = -Infinity;
  
  function dfs(node: TreeNode | null): number {
    if (!node) return 0;
    
    const left = Math.max(0, dfs(node.left));
    const right = Math.max(0, dfs(node.right));
    
    const currentMax = node.val + left + right;
    maxSum = Math.max(maxSum, currentMax);
    
    return node.val + Math.max(left, right);
  }
  
  dfs(root);
  return maxSum;
}`,
    },
    {
      title: "Design Twitter",
      description: "Design a simplified version of Twitter where users can post tweets, follow/unfollow other users, and see the 10 most recent tweets in their news feed.",
      category: "SYSTEM_DESIGN",
      difficulty: "HARD",
      company: "Twitter",
      tags: ["system-design", "social-media"],
      type: "SYSTEM_DESIGN",
      hints: [
        "Consider read-heavy vs write-heavy operations",
        "Use fan-out approach for news feed",
        "Think about caching strategies",
        "Consider database partitioning",
      ],
      solution: `Key Components:
1. User Service
   - User profiles and authentication
   - Follow/unfollow relationships
   
2. Tweet Service
   - Create, read, delete tweets
   - Store tweets in distributed database
   
3. News Feed Service
   - Fan-out approach: pre-compute feeds
   - Store feeds in cache (Redis)
   - Fallback to on-the-fly generation
   
4. Timeline Service
   - User's own tweets
   - Merge with news feed
   
5. Database Design
   - Tweets: tweet_id, user_id, content, timestamp
   - Follows: follower_id, followee_id
   - Feeds: user_id, tweet_ids (sorted)
   
6. Caching Strategy
   - Cache top 100 tweets per user
   - Use write-through cache
   - Invalidate on new tweets`,
    },
  ]

  for (const question of questions) {
    await prisma.question.create({
      data: question,
    })
  }

  console.log('Database seeded successfully!')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

