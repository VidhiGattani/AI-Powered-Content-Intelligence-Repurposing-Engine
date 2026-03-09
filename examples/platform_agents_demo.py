"""
Demo script showing how to use platform agents

This script demonstrates how to generate platform-specific content
using the platform agents with Claude Sonnet 3.5 via Amazon Bedrock.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.platform_agents import (
    PlatformAgentFactory,
    StylePatterns,
    LinkedInAgent,
    TwitterAgent,
    InstagramAgent,
    YouTubeShortsAgent
)
from src.models.enums import Platform


def main():
    """Demo the platform agents"""
    
    # Sample data
    topics = [
        "AI and machine learning trends",
        "Content creation strategies",
        "Building authentic connections",
        "Social media best practices"
    ]
    
    style_patterns = StylePatterns(
        examples=[
            "This is my first example post. It's authentic and engaging.",
            "Here's another example. I love sharing insights with my audience!",
            "Final example showing my unique voice and style."
        ],
        sentence_structure="Short, punchy sentences with occasional longer explanations",
        vocabulary="Professional yet accessible, avoiding jargon",
        tone="Friendly, enthusiastic, and authentic",
        emoji_usage="Moderate - 2-3 emojis per post for emphasis"
    )
    
    original_content = """
    In today's digital landscape, creating authentic content is more important than ever.
    AI tools are revolutionizing how we approach content creation, but the human touch
    remains essential. The key is finding the right balance between automation and authenticity.
    
    When building your content strategy, focus on understanding your audience deeply.
    What are their pain points? What keeps them up at night? Address these concerns
    directly and provide actionable solutions.
    
    Remember, consistency beats perfection. It's better to publish regularly with good
    content than to wait for the perfect post that never comes.
    """
    
    print("=" * 80)
    print("PLATFORM AGENTS DEMO")
    print("=" * 80)
    print()
    
    # Demo each platform
    platforms = [
        (Platform.LINKEDIN, "LinkedIn Post"),
        (Platform.TWITTER, "Twitter Thread"),
        (Platform.INSTAGRAM, "Instagram Caption"),
        (Platform.YOUTUBE_SHORTS, "YouTube Shorts Script")
    ]
    
    for platform, name in platforms:
        print(f"\n{'=' * 80}")
        print(f"{name.upper()}")
        print(f"{'=' * 80}\n")
        
        # Create agent
        agent = PlatformAgentFactory.create_agent(platform)
        
        # Show constraints
        constraints = agent.get_constraints()
        print(f"Constraints:")
        print(f"  - Length: {constraints.min_length}-{constraints.max_length}")
        print(f"  - Format: {', '.join(constraints.format_requirements or [])}")
        print(f"  - Style: {', '.join(constraints.style_guidelines or [])}")
        print()
        
        # Note: Actual generation requires AWS credentials and Bedrock access
        print("Note: To generate actual content, you need:")
        print("  1. AWS credentials configured")
        print("  2. Access to Amazon Bedrock")
        print("  3. Claude Sonnet 3.5 model enabled")
        print()
        
        # Show example validation
        if platform == Platform.LINKEDIN:
            test_content = " ".join(["word"] * 200) + " What do you think?"
            result = agent.validate(test_content)
            print(f"Validation example (200 words + question):")
            print(f"  - Valid: {result.is_valid}")
            print(f"  - Errors: {result.errors}")
            print(f"  - Warnings: {result.warnings}")
        
        elif platform == Platform.TWITTER:
            test_content = [
                "Tweet 1 with some content",
                "Tweet 2 with more content",
                "Tweet 3 continuing",
                "Tweet 4 with insights",
                "Tweet 5 wrapping up"
            ]
            result = agent.validate(test_content)
            print(f"Validation example (5 tweets):")
            print(f"  - Valid: {result.is_valid}")
            print(f"  - Errors: {result.errors}")
            print(f"  - Warnings: {result.warnings}")
        
        elif platform == Platform.INSTAGRAM:
            test_content = " ".join(["word"] * 125) + " 🎯 💫 ✨"
            result = agent.validate(test_content)
            print(f"Validation example (125 words + emojis):")
            print(f"  - Valid: {result.is_valid}")
            print(f"  - Errors: {result.errors}")
            print(f"  - Warnings: {result.warnings}")
        
        elif platform == Platform.YOUTUBE_SHORTS:
            test_content = """[00:00] HOOK
Voiceover: Amazing hook
Visual: Bold text
B-roll: Exciting footage

[00:30] CONTENT
Voiceover: Main content
Visual: Engaging visuals
B-roll: Supporting footage

[00:45] CTA
Voiceover: Call to action
Visual: Subscribe button
B-roll: Like animation"""
            result = agent.validate(test_content)
            print(f"Validation example (45s script):")
            print(f"  - Valid: {result.is_valid}")
            print(f"  - Errors: {result.errors}")
            print(f"  - Warnings: {result.warnings}")
    
    print(f"\n{'=' * 80}")
    print("USAGE EXAMPLE")
    print(f"{'=' * 80}\n")
    
    print("""
# To use in your code:

from src.services.platform_agents import PlatformAgentFactory, StylePatterns
from src.models.enums import Platform

# Create agent for desired platform
agent = PlatformAgentFactory.create_agent(Platform.LINKEDIN)

# Generate content (requires AWS Bedrock access)
result = agent.generate(
    topics=["AI trends", "Content strategy"],
    style_patterns=style_patterns,
    original_content="Your long-form content here..."
)

# Validate generated content
validation = agent.validate(result.content)
if validation.is_valid:
    print("Content is ready to publish!")
else:
    print(f"Issues found: {validation.errors}")

# Get platform constraints
constraints = agent.get_constraints()
print(f"Platform requirements: {constraints}")
""")


if __name__ == "__main__":
    main()
