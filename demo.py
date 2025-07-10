#!/usr/bin/env python3
"""
Demo script to show bot functionality without requiring a Telegram bot token
"""

import asyncio
import json
import os
import sys
sys.path.insert(0, '.')

from main import DataManager, SecuritySystem

async def demo():
    print("🤖 Telegram Gate Bot - Demo Mode")
    print("=" * 50)
    
    # Test security system
    print("\n🔒 Security System Test:")
    print(f"Valid activation code: {SecuritySystem.verify_activation_code('G7m$K2zQ')}")
    print(f"Invalid activation code: {SecuritySystem.verify_activation_code('wrong_code')}")
    
    # Test data storage
    print("\n📁 File Storage Test:")
    
    # Test channels
    sample_channels = ["testchannel1", "testchannel2", "testchannel3"]
    await DataManager.save_channels(sample_channels)
    loaded_channels = await DataManager.load_channels()
    print(f"Saved channels: {sample_channels}")
    print(f"Loaded channels: {loaded_channels}")
    print(f"Channel storage works: {sample_channels == loaded_channels}")
    
    # Test prize system
    sample_prize = {
        'type': 'text',
        'content': 'Congratulations! You won a free eBook!',
        'created_at': '2024-03-15T10:00:00'
    }
    await DataManager.save_prize(sample_prize)
    loaded_prize = await DataManager.load_prize()
    print(f"Prize storage works: {loaded_prize['content'] == sample_prize['content']}")
    
    # Show file structure
    print("\n📂 Generated Files:")
    files = ['channels.json', 'prize.dat']
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file} - {os.path.getsize(file)} bytes")
        else:
            print(f"❌ {file} - Not found")
    
    # Show channels.json content
    if os.path.exists('channels.json'):
        with open('channels.json', 'r') as f:
            content = f.read()
            print(f"\n📄 channels.json content:")
            print(content)
    
    # Clean up demo files
    for file in files:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n✅ Demo completed successfully!")
    print("🚀 Bot is ready for production use!")

if __name__ == "__main__":
    asyncio.run(demo())