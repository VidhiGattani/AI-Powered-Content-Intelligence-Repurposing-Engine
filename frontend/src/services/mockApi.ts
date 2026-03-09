/**
 * Mock API Service for Local Testing
 * This simulates all backend responses without requiring AWS deployment
 * Data persists in localStorage to simulate a real database
 */

// Mock delay to simulate network requests
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// LocalStorage keys
const STORAGE_KEYS = {
  USERS: 'mock_users',
  CONTENTS: 'mock_contents',
  GENERATED: 'mock_generated',
  SCHEDULES: 'mock_schedules',
  STYLE_PROFILE: 'mock_style_profile',
  STYLE_CONTENTS: 'mock_style_contents',
  CURRENT_USER: 'mock_current_user',
};

// Helper functions for localStorage
const getFromStorage = (key: string, defaultValue: any = []) => {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : defaultValue;
  } catch {
    return defaultValue;
  }
};

const saveToStorage = (key: string, value: any) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error('Failed to save to localStorage:', e);
  }
};

// Mock data storage with persistence
let mockUsers: any[] = getFromStorage(STORAGE_KEYS.USERS);
let mockContents: any[] = getFromStorage(STORAGE_KEYS.CONTENTS);
let mockGeneratedContent: any[] = getFromStorage(STORAGE_KEYS.GENERATED);
let mockSchedules: any[] = getFromStorage(STORAGE_KEYS.SCHEDULES);
let mockStyleProfile = getFromStorage(STORAGE_KEYS.STYLE_PROFILE, { content_count: 0, status: 'incomplete', embeddings_generated: false, contents: [] });
let mockStyleContents: any[] = getFromStorage(STORAGE_KEYS.STYLE_CONTENTS);
let currentUser: any = getFromStorage(STORAGE_KEYS.CURRENT_USER, null);

// Generate mock IDs
const generateId = () => `mock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const mockAuthService = {
  signup: async (email: string, password: string, name: string) => {
    await delay(800);
    
    // Check if user already exists
    const existingUser = mockUsers.find(u => u.email === email);
    if (existingUser) {
      throw new Error('User already exists with this email');
    }
    
    const user = {
      user_id: generateId(),
      email,
      name,
    };
    mockUsers.push({ ...user, password });
    saveToStorage(STORAGE_KEYS.USERS, mockUsers);
    
    currentUser = user;
    saveToStorage(STORAGE_KEYS.CURRENT_USER, currentUser);
    
    // Store token
    localStorage.setItem('access_token', 'mock-token-' + generateId());
    
    return user;
  },

  signin: async (email: string, password: string) => {
    await delay(800);
    const user = mockUsers.find(u => u.email === email && u.password === password);
    if (!user) {
      throw new Error('Invalid credentials');
    }
    currentUser = { user_id: user.user_id, email: user.email, name: user.name };
    saveToStorage(STORAGE_KEYS.CURRENT_USER, currentUser);
    
    const token = 'mock-token-' + generateId();
    localStorage.setItem('access_token', token);
    
    return {
      access_token: token,
      refresh_token: 'mock-refresh-' + generateId(),
      expires_in: 3600,
      user_id: user.user_id,
      name: user.name,
    };
  },

  signout: async () => {
    await delay(300);
    currentUser = null;
    saveToStorage(STORAGE_KEYS.CURRENT_USER, null);
    localStorage.removeItem('access_token');
    return { message: 'Signed out successfully' };
  },
};

export const mockStyleService = {
  uploadStyleContent: async (filename: string, content: string) => {
    await delay(1500);
    
    const styleContent = {
      id: generateId(),
      filename,
      content: content.substring(0, 200) + '...', // Store preview
      uploaded_at: new Date().toISOString(),
      status: 'uploaded',
      s3_key: `style-vault/mock-user/${filename}`,
    };
    
    mockStyleContents.push(styleContent);
    saveToStorage(STORAGE_KEYS.STYLE_CONTENTS, mockStyleContents);
    
    mockStyleProfile.content_count += 1;
    mockStyleProfile.contents = mockStyleContents;
    if (mockStyleProfile.content_count >= 3) {
      mockStyleProfile.status = 'ready';
      mockStyleProfile.embeddings_generated = true;
    }
    saveToStorage(STORAGE_KEYS.STYLE_PROFILE, mockStyleProfile);
    
    return {
      content_id: styleContent.id,
      filename,
      status: 'uploaded',
      s3_key: styleContent.s3_key,
    };
  },

  getStyleProfile: async () => {
    await delay(500);
    return {
      user_id: currentUser?.user_id || 'mock-user',
      ...mockStyleProfile,
      contents: mockStyleContents, // Include uploaded contents
    };
  },

  deleteStyleContent: async (id: string) => {
    await delay(500);
    mockStyleContents = mockStyleContents.filter(c => c.id !== id);
    saveToStorage(STORAGE_KEYS.STYLE_CONTENTS, mockStyleContents);
    
    mockStyleProfile.content_count = mockStyleContents.length;
    mockStyleProfile.contents = mockStyleContents;
    if (mockStyleProfile.content_count < 3) {
      mockStyleProfile.status = 'incomplete';
      mockStyleProfile.embeddings_generated = false;
    }
    saveToStorage(STORAGE_KEYS.STYLE_PROFILE, mockStyleProfile);
    
    return { message: 'Style content deleted successfully' };
  },
};

export const mockContentService = {
  uploadContent: async (filename: string, content: string) => {
    await delay(2000);
    const newContent = {
      content_id: generateId(),
      filename,
      upload_date: new Date().toISOString(),
      status: filename.match(/\.(mp4|mov|avi|mp3|wav)$/i) ? 'processing' : 'transcribed',
      content_preview: content.substring(0, 500),
    };
    mockContents.push(newContent);
    saveToStorage(STORAGE_KEYS.CONTENTS, mockContents);
    
    // Simulate transcription completion after 3 seconds
    if (newContent.status === 'processing') {
      setTimeout(() => {
        newContent.status = 'transcribed';
        saveToStorage(STORAGE_KEYS.CONTENTS, mockContents);
      }, 3000);
    }
    
    return newContent;
  },

  listContent: async (limit = 10, offset = 0) => {
    await delay(500);
    return {
      items: mockContents.slice(offset, offset + limit),
      total: mockContents.length,
      limit,
      offset,
    };
  },

  getContent: async (id: string) => {
    await delay(500);
    const content = mockContents.find(c => c.content_id === id);
    if (!content) throw new Error('Content not found');
    return {
      ...content,
      transcript: content.content_preview || 'This is a mock transcript of the content. In the real system, this would be the actual transcription from Amazon Transcribe.',
      topics: ['AI', 'Technology', 'Innovation', 'Content Creation', 'Social Media'],
    };
  },

  deleteContent: async (id: string) => {
    await delay(500);
    mockContents = mockContents.filter(c => c.content_id !== id);
    saveToStorage(STORAGE_KEYS.CONTENTS, mockContents);
    return { message: 'Content deleted successfully' };
  },
};

export const mockGenerationService = {
  generate: async (contentId: string, platforms: string[]) => {
    await delay(3000);
    
    // Get the actual content to make generation more relevant
    const sourceContent = mockContents.find(c => c.content_id === contentId);
    const contentPreview = sourceContent?.content_preview || sourceContent?.filename || 'your content';
    const fullContent = sourceContent?.content_preview || '';
    const filename = sourceContent?.filename || 'content';
    const timestamp = new Date().toLocaleString();
    
    // Extract key topics from the content (simple keyword extraction)
    const extractTopics = (text: string): string[] => {
      const commonWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their']);
      const words = text.toLowerCase().match(/\b[a-z]{4,}\b/g) || [];
      const wordFreq: { [key: string]: number } = {};
      
      words.forEach(word => {
        if (!commonWords.has(word)) {
          wordFreq[word] = (wordFreq[word] || 0) + 1;
        }
      });
      
      return Object.entries(wordFreq)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([word]) => word.charAt(0).toUpperCase() + word.slice(1));
    };
    
    const topics = extractTopics(fullContent);
    const topicsText = topics.length > 0 ? topics.join(', ') : 'innovation, content creation, digital transformation';
    
    // Create a summary of the content (first 200 chars)
    const contentSummary = fullContent.length > 200 
      ? fullContent.substring(0, 200) + '...' 
      : fullContent || `insights from ${filename}`;
    
    const results: any = {};
    
    platforms.forEach(platform => {
      const generatedId = generateId();
      let text = '';
      
      // Generate varied content based on the source
      const variation = Math.floor(Math.random() * 3);
      
      switch (platform) {
        case 'LINKEDIN':
          if (variation === 0) {
            text = `🚀 Key insights from: "${filename}"\n\n${contentSummary}\n\nAfter analyzing this content, here are the main takeaways:\n\n1. ${topics[0] || 'Innovation'} - Understanding the fundamentals is crucial\n2. ${topics[1] || 'Strategy'} - Implementation requires careful planning\n3. ${topics[2] || 'Growth'} - Continuous improvement drives success\n\nThese insights around ${topicsText} are particularly relevant in today's landscape.\n\nWhat's your perspective on ${topics[0] || 'this topic'}? I'd love to hear your thoughts in the comments! 👇\n\n#${topics[0] || 'Innovation'} #${topics[1] || 'Strategy'} #ProfessionalDevelopment\n\n[Generated from: ${filename}]`;
          } else if (variation === 1) {
            text = `💡 Sharing valuable insights from my latest content on ${topicsText}\n\n"${contentSummary}"\n\nThe landscape around ${topics[0] || 'this topic'} is evolving rapidly, and staying ahead requires continuous learning and adaptation.\n\nKey points to consider:\n• ${topics[0] || 'Innovation'} drives competitive advantage\n• ${topics[1] || 'Strategy'} requires both vision and execution\n• ${topics[2] || 'Growth'} comes from consistent effort\n\nHow are you approaching ${topics[0] || 'these challenges'}? Let's discuss!\n\n#${topics[0] || 'Leadership'} #${topics[1] || 'Growth'} #ThoughtLeadership\n\n[Generated from: ${filename}]`;
          } else {
            text = `📊 Analysis and insights worth sharing\n\nBased on my recent work with ${filename}:\n\n"${contentSummary}"\n\nThe data around ${topicsText} shows that success comes from:\n✓ Deep understanding of ${topics[0] || 'fundamentals'}\n✓ Strategic application of ${topics[1] || 'best practices'}\n✓ Continuous focus on ${topics[2] || 'improvement'}\n\nWhat strategies have worked for you in ${topics[0] || 'this area'}? Share below!\n\n#${topics[0] || 'Business'} #${topics[1] || 'Analytics'} #DataDriven\n\n[Generated from: ${filename}]`;
          }
          break;
          
        case 'TWITTER':
          if (variation === 0) {
            text = `1/ 🧵 Thread on: ${contentPreview.substring(0, 40)}...\n\n2/ The key insight here is understanding the fundamentals before diving into advanced concepts.\n\n3/ Three things that matter most:\n- Clarity of purpose\n- Consistent execution\n- Authentic engagement\n\n4/ This approach has proven effective across different contexts and industries.\n\n5/ The future belongs to those who can adapt while staying true to their core values.\n\n6/ What's your take? Reply with your thoughts! 💭\n\n[Generated: ${timestamp}]`;
          } else if (variation === 1) {
            text = `🔥 Hot take on ${contentPreview.substring(0, 30)}...\n\nMost people get this wrong because they focus on tactics instead of strategy.\n\nThe real secret? Start with WHY, then figure out HOW.\n\nRetweet if you agree! 🔄\n\n[Generated: ${timestamp}]`;
          } else {
            text = `💭 Quick thoughts:\n\n"${contentPreview.substring(0, 60)}..."\n\nThis resonates because it addresses a real problem with a practical solution.\n\nThe best part? It's actionable TODAY.\n\nWho else is implementing this? 👇\n\n[Generated: ${timestamp}]`;
          }
          break;
          
        case 'INSTAGRAM':
          if (variation === 0) {
            text = `✨ Transform your perspective ✨\n\nInspired by: "${contentPreview.substring(0, 40)}..."\n\nHere's what I learned:\n\n🎯 Focus on what matters\n💪 Take consistent action\n🌟 Stay authentic to your vision\n\nThe journey is just as important as the destination. Every step forward counts! 📈\n\nDouble tap if this resonates with you! ❤️\n\n#Motivation #Growth #Success #Inspiration #MindsetMatters\n\n[Generated: ${timestamp}]`;
          } else if (variation === 1) {
            text = `🌈 Real talk time 🌈\n\nBased on "${contentPreview.substring(0, 35)}..."\n\nThe truth? Success isn't about perfection. It's about:\n\n✓ Showing up consistently\n✓ Learning from mistakes\n✓ Staying true to yourself\n\nYour journey is unique. Embrace it! 💫\n\nTag someone who needs to see this! 👇\n\n#RealTalk #Authenticity #PersonalGrowth #Mindset\n\n[Generated: ${timestamp}]`;
          } else {
            text = `💡 Game-changing insight 💡\n\nFrom: "${contentPreview.substring(0, 45)}..."\n\nWhat if I told you that small changes lead to big results? 🚀\n\nStart here:\n1️⃣ Define your goal\n2️⃣ Break it into steps\n3️⃣ Take action TODAY\n\nYour future self will thank you! 🙏\n\nSave this for later! 📌\n\n#Goals #Action #Results #Transformation\n\n[Generated: ${timestamp}]`;
          }
          break;
          
        case 'YOUTUBE_SHORTS':
          if (variation === 0) {
            text = `[YOUTUBE SHORTS SCRIPT]\n\nTitle: "${contentPreview.substring(0, 40)}..."\n\n[0:00-0:03] 🎣 HOOK: "You're doing this WRONG!"\n\n[0:03-0:08] 😰 PROBLEM: "Most people waste time on the wrong approach"\n\n[0:08-0:18] 💡 SOLUTION: "Here's the 3-step method that actually works:\n1. Start with clarity\n2. Focus on execution\n3. Measure and adjust"\n\n[0:18-0:25] 🎯 BENEFIT: "This saves hours and gets better results"\n\n[0:25-0:30] 📢 CTA: "Follow for more tips! Link in bio!"\n\n📹 VISUAL NOTES:\n- Fast cuts every 2-3 seconds\n- Text overlays for key points\n- Energetic background music\n- End with subscribe animation\n\n[Generated: ${timestamp}]`;
          } else if (variation === 1) {
            text = `[YOUTUBE SHORTS SCRIPT]\n\nBased on: "${contentPreview.substring(0, 35)}..."\n\n[0:00-0:04] 🔥 HOOK: "This changed everything for me!"\n\n[0:04-0:10] 📖 STORY: "I used to struggle with this until I discovered..."\n\n[0:10-0:20] 🎓 LESSON: "The secret is understanding these 3 principles:\n• Principle 1: Focus\n• Principle 2: Consistency\n• Principle 3: Adaptation"\n\n[0:20-0:27] ✅ RESULT: "Now I get 10x better results in half the time"\n\n[0:27-0:30] 👆 CTA: "Try it yourself - comment your results!"\n\n📹 PRODUCTION:\n- Dynamic transitions\n- Emoji overlays\n- Upbeat music\n- Strong call-to-action\n\n[Generated: ${timestamp}]`;
          } else {
            text = `[YOUTUBE SHORTS SCRIPT]\n\nTopic: ${contentPreview.substring(0, 40)}...\n\n[0:00-0:03] ⚡ HOOK: "Stop! You need to hear this!"\n\n[0:03-0:12] 🤔 QUESTION: "Why do some people succeed while others struggle? It's not luck..."\n\n[0:12-0:22] 💎 ANSWER: "It's about these 3 things:\n1. Clear vision\n2. Daily action\n3. Never giving up"\n\n[0:22-0:28] 🚀 MOTIVATION: "You have everything you need to start TODAY"\n\n[0:28-0:30] 💬 CTA: "Comment 'YES' if you're ready!"\n\n📹 STYLE:\n- High energy\n- Quick pacing\n- Motivational tone\n- Strong visuals\n\n[Generated: ${timestamp}]`;
          }
          break;
      }
      
      results[platform] = {
        generated_id: generatedId,
        text,
        status: 'success',
      };
      
      mockGeneratedContent.push({
        generated_id: generatedId,
        content_id: contentId,
        platform,
        text,
        version: 1,
        status: 'draft',
        created_at: new Date().toISOString(),
      });
    });
    
    saveToStorage(STORAGE_KEYS.GENERATED, mockGeneratedContent);
    
    return {
      generation_id: generateId(),
      results,
    };
  },

  regenerate: async (id: string) => {
    await delay(2000);
    const original = mockGeneratedContent.find(c => c.generated_id === id);
    if (!original) throw new Error('Content not found');
    
    // Create a new variation
    const variations = [
      '\n\n[Regenerated with fresh perspective and new angle]',
      '\n\n[Regenerated with different tone and emphasis]',
      '\n\n[Regenerated with alternative approach]',
    ];
    const variation = variations[Math.floor(Math.random() * variations.length)];
    
    const newVersion = {
      ...original,
      generated_id: generateId(),
      text: original.text.split('[Generated:')[0] + variation + `\n[Generated: ${new Date().toLocaleString()}]`,
      version: original.version + 1,
      created_at: new Date().toISOString(),
    };
    
    mockGeneratedContent.push(newVersion);
    saveToStorage(STORAGE_KEYS.GENERATED, mockGeneratedContent);
    return newVersion;
  },

  getGenerated: async (id: string) => {
    await delay(500);
    const content = mockGeneratedContent.find(c => c.generated_id === id);
    if (!content) throw new Error('Content not found');
    return content;
  },

  editContent: async (id: string, editedText: string) => {
    await delay(500);
    const content = mockGeneratedContent.find(c => c.generated_id === id);
    if (!content) throw new Error('Content not found');
    content.text = editedText;
    content.edited = true;
    content.edited_at = new Date().toISOString();
    saveToStorage(STORAGE_KEYS.GENERATED, mockGeneratedContent);
    return content;
  },

  approveContent: async (id: string) => {
    await delay(500);
    const content = mockGeneratedContent.find(c => c.generated_id === id);
    if (!content) throw new Error('Content not found');
    content.status = 'approved';
    content.approved_at = new Date().toISOString();
    saveToStorage(STORAGE_KEYS.GENERATED, mockGeneratedContent);
    return content;
  },
};

export const mockSeoService = {
  generateTitles: async (_content: string, _platform: string) => {
    await delay(1500);
    return {
      titles: [
        'How AI is Transforming Content Creation in 2024',
        '5 Ways to Repurpose Your Content with AI',
        'The Ultimate Guide to AI-Powered Content Strategy',
        'Why Every Creator Needs AI Tools in Their Workflow',
        'Content Creation Made Easy: The AI Revolution',
      ],
    };
  },

  generateHashtags: async (_content: string, _platform: string) => {
    await delay(1000);
    return {
      hashtags: ['#AI', '#ContentCreation', '#DigitalMarketing', '#SocialMedia', '#CreatorEconomy', '#Innovation'],
    };
  },

  generateAltText: async (imageDescription: string) => {
    await delay(1000);
    return {
      alt_text: `Professional workspace showing ${imageDescription}, representing modern content creation workflow with AI-powered tools`,
    };
  },
};

export const mockScheduleService = {
  createSchedule: async (
    generatedContentId: string,
    platform: string,
    scheduledTime: string,
    timezone: string = 'Asia/Kolkata' // Default to IST
  ) => {
    await delay(800);
    const schedule = {
      schedule_id: generateId(),
      generated_content_id: generatedContentId,
      platform,
      scheduled_time: scheduledTime,
      timezone,
      status: 'scheduled',
      created_at: new Date().toISOString(),
      notification_sent: true, // Simulate email notification
    };
    mockSchedules.push(schedule);
    saveToStorage(STORAGE_KEYS.SCHEDULES, mockSchedules);
    
    // Simulate email notification
    console.log(`📧 Email notification sent to ${currentUser?.email || 'user@example.com'}`);
    console.log(`   Content scheduled for ${platform} at ${scheduledTime} ${timezone}`);
    
    return {
      ...schedule,
      message: `Schedule created successfully! Confirmation email sent to ${currentUser?.email || 'your email'}.`,
    };
  },

  listSchedules: async () => {
    await delay(500);
    // Enrich schedules with generated content info
    const enrichedSchedules = mockSchedules.map(schedule => {
      const generatedContent = mockGeneratedContent.find(
        c => c.generated_id === schedule.generated_content_id
      );
      return {
        ...schedule,
        content_preview: generatedContent?.text.substring(0, 100) + '...' || 'Content preview',
        platform_name: schedule.platform,
      };
    });
    return {
      schedules: enrichedSchedules,
    };
  },

  deleteSchedule: async (id: string) => {
    await delay(500);
    mockSchedules = mockSchedules.filter(s => s.schedule_id !== id);
    saveToStorage(STORAGE_KEYS.SCHEDULES, mockSchedules);
    return { message: 'Schedule deleted successfully' };
  },

  getOptimalTimes: async (platform: string, timezone: string = 'Asia/Kolkata') => {
    await delay(500);
    const times: any = {
      LINKEDIN: [
        { day: 'Tuesday', time: '09:00:00', reason: 'Peak engagement for professionals' },
        { day: 'Wednesday', time: '12:00:00', reason: 'Lunch break browsing' },
        { day: 'Thursday', time: '10:00:00', reason: 'Mid-week high activity' },
      ],
      TWITTER: [
        { day: 'Monday', time: '08:00:00', reason: 'Morning commute time' },
        { day: 'Wednesday', time: '15:00:00', reason: 'Afternoon break' },
        { day: 'Friday', time: '17:00:00', reason: 'End of workday' },
      ],
      INSTAGRAM: [
        { day: 'Wednesday', time: '11:00:00', reason: 'Mid-morning scroll' },
        { day: 'Friday', time: '13:00:00', reason: 'Lunch break engagement' },
        { day: 'Sunday', time: '19:00:00', reason: 'Evening relaxation' },
      ],
      YOUTUBE_SHORTS: [
        { day: 'Friday', time: '18:00:00', reason: 'Weekend starts' },
        { day: 'Saturday', time: '20:00:00', reason: 'Prime evening viewing' },
        { day: 'Sunday', time: '21:00:00', reason: 'Late night entertainment' },
      ],
    };
    return { optimal_times: times[platform] || times.LINKEDIN, timezone };
  },
};
