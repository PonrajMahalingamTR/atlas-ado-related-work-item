#!/usr/bin/env python3
"""
Main Application Runner - OpenArena Integration Demo
"""

import sys
import os
import asyncio
import time
import argparse

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def run_main_application(model: str = "gemini2pro"):
    """Run the main application with OpenArena integration"""
    print("🚀 OpenArena Integration - Main Application")
    print("=" * 60)
    print(f"🤖 Using AI Model: {model}")
    print("=" * 60)
    
    try:
        from openarena.websocket_client import OpenArenaWebSocketClient
        
        # Create OpenArena client
        client = OpenArenaWebSocketClient()
        print("✅ OpenArena client created successfully")
        print(f"🌐 Endpoint: {client.base_url}")
        print(f"⏱️ Default timeout: {client.config.timeout} seconds")
        print(f"🔧 Available models: {', '.join(client.workflow_ids.keys())}")
        print(f"🎯 Selected model: {model}")
        
        # Validate model selection
        if model not in client.workflow_ids:
            print(f"⚠️ Warning: Model '{model}' not found in configuration")
            print(f"   Available models: {', '.join(client.workflow_ids.keys())}")
            print(f"   Falling back to 'gemini2pro'")
            model = "gemini2pro"
        
        # Sample meeting transcript for backlog refinement
        sample_transcript = """
        Today we discussed the user registration epic. We need to implement email verification, 
        password reset functionality, and social media login. The user story for email verification 
        should be high priority. We decided to use OAuth for social media integration.
        
        Key decisions made:
        - Email verification will be mandatory for all new users
        - Password reset will use secure token-based approach
        - Social media login will support Google, Facebook, and LinkedIn
        - User profile management needs to be enhanced
        
        Action items:
        - John will research OAuth providers
        - Sarah will design the email verification flow
        - Mike will estimate development effort
        """
        
        # Sample parsed content
        sample_parsed_content = {
            "epics": [
                {"title": "User Registration", "description": "User registration system"}
            ],
            "features": [
                {"title": "Email Verification", "description": "Email verification feature"},
                {"title": "Password Reset", "description": "Password reset functionality"}
            ],
            "user_stories": [
                {"title": "As a user, I want to register with email", "description": "User registration flow"}
            ],
            "action_items": [
                {"title": "Research OAuth providers", "assignee": "John"},
                {"title": "Design email verification", "assignee": "Sarah"},
                {"title": "Estimate development effort", "assignee": "Mike"}
            ],
            "decisions": [
                {"title": "OAuth for social media", "decision": "Use OAuth for social login"}
            ]
        }
        
        print(f"\n📝 Sample Transcript Length: {len(sample_transcript)} characters")
        print(f"📋 Current Items: {len(sample_parsed_content['epics'])} epics, {len(sample_parsed_content['features'])} features")
        
        print(f"\n🔄 Starting Backlog Refinement with OpenArena using {model}...")
        print("   This will attempt to connect to OpenArena API")
        print("   If it times out, it will fall back to mock client")
        
        start_time = time.time()
        
        # Run backlog refinement
        refined_items = await client.refine_backlog_items(
            sample_transcript, 
            sample_parsed_content, 
            model
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️ Refinement completed in {elapsed_time:.2f} seconds")
        
        # Display results
        if refined_items and 'refinement_metadata' in refined_items:
            processing_method = refined_items['refinement_metadata'].get('processing_method', 'unknown')
            model_used = refined_items['refinement_metadata'].get('model_used', 'unknown')
            print(f"✅ Processing method: {processing_method}")
            print(f"🤖 Model used: {model_used}")
            
            # Show refined items
            epics = refined_items.get('refined_epics', [])
            features = refined_items.get('refined_features', [])
            user_stories = refined_items.get('refined_user_stories', [])
            action_items = refined_items.get('refined_action_items', [])
            decisions = refined_items.get('refined_decisions', [])
            
            print(f"\n📊 Refinement Results:")
            print(f"   🎯 Epics: {len(epics)}")
            print(f"   ⚙️ Features: {len(features)}")
            print(f"   👥 User Stories: {len(user_stories)}")
            print(f"   ✅ Action Items: {len(action_items)}")
            print(f"   🤔 Decisions: {len(decisions)}")
            
            # Show sample refined items
            if epics:
                print(f"\n🎯 Sample Epic:")
                epic = epics[0]
                print(f"   Title: {epic.get('title', 'N/A')}")
                print(f"   Priority: {epic.get('priority', 'N/A')}")
                print(f"   Status: {epic.get('status', 'N/A')}")
            
            if features:
                print(f"\n⚙️ Sample Feature:")
                feature = features[0]
                print(f"   Title: {feature.get('title', 'N/A')}")
                print(f"   Priority: {feature.get('priority', 'N/A')}")
                print(f"   Epic ID: {feature.get('epic_id', 'N/A')}")
            
            # Show insights if available
            insights = refined_items.get('refinement_insights', {})
            if insights:
                print(f"\n💡 Refinement Insights:")
                for key, value in insights.items():
                    if isinstance(value, list) and value:
                        print(f"   {key.replace('_', ' ').title()}: {len(value)} items")
                    elif value and value != "To be assessed":
                        print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Show next steps
            next_steps = refined_items.get('next_steps', [])
            if next_steps:
                print(f"\n🚀 Next Steps:")
                for i, step in enumerate(next_steps[:3], 1):  # Show first 3
                    print(f"   {i}. {step}")
                if len(next_steps) > 3:
                    print(f"   ... and {len(next_steps) - 3} more")
            
            print(f"\n🎉 Application completed successfully!")
            print(f"   Processing method: {processing_method}")
            print(f"   Model used: {model_used}")
            print(f"   Total time: {elapsed_time:.2f} seconds")
            
        else:
            print("❌ Refinement failed - no results returned")
            
    except Exception as e:
        print(f"❌ Application failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description="OpenArena Integration Demo")
    parser.add_argument(
        "--model", 
        choices=["claude4opus", "gpt5", "gemini2pro", "azuredevopsagent"],
        default="gemini2pro",
        help="AI model to use for refinement (default: gemini2pro)"
    )
    
    args = parser.parse_args()
    
    print("Starting OpenArena Integration Application...")
    print(f"Selected model: {args.model}")
    asyncio.run(run_main_application(args.model))

if __name__ == "__main__":
    main()
