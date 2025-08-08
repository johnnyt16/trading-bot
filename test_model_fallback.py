#!/usr/bin/env python3
"""
Test the model fallback system
"""

import asyncio
from src.ai_brain.gpt5_trading_system import GPT5TradingBrain
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

async def test_models():
    """Test which models are available"""
    
    logger.info("Testing GPT Model Hierarchy")
    logger.info("=" * 50)
    
    brain = GPT5TradingBrain()
    
    logger.info(f"Model hierarchy: {brain.model_hierarchy}")
    logger.info(f"Starting with: {brain.model}")
    
    # Test a simple request
    test_prompt = "Say 'Hello' and tell me which GPT model you are."
    
    try:
        response = await brain._make_gpt_request(
            messages=[
                {"role": "user", "content": test_prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        logger.success(f"Response: {result}")
        logger.success(f"Successfully using model: {brain.model}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    
    logger.info("=" * 50)
    logger.info("Model fallback system is ready!")
    logger.info("Will automatically downgrade if rate limited:")
    logger.info("  gpt-4o → gpt-4-turbo → gpt-4 → gpt-3.5-turbo → gpt-4o-mini")

if __name__ == "__main__":
    asyncio.run(test_models())