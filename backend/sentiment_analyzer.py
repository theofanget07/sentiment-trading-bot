import os
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of crypto/trading news using Perplexity API.
    
    Args:
        text: Article text or news snippet to analyze
        
    Returns:
        dict with keys:
        - sentiment: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        - confidence: float 0-100
        - reasoning: str explanation
        - key_points: list of important points
        - sources: list of sources (Perplexity bonus!)
    """
    
    if not text or len(text.strip()) < 10:
        return {
            'sentiment': 'NEUTRAL',
            'confidence': 0,
            'reasoning': 'Text too short to analyze',
            'key_points': [],
            'sources': []
        }
    
    # Construct prompt for Perplexity
    prompt = f"""You are a professional crypto/trading sentiment analyst.

Analyze the following text and determine if it's BULLISH (positive for price), BEARISH (negative for price), or NEUTRAL.

Text to analyze:
\"\"\"
{text[:2000]}
\"\"\"

Provide your analysis in this exact format:

SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
REASONING: [One sentence explanation]
KEY_POINTS:
- [Point 1]
- [Point 2]
- [Point 3]

Be objective and focus on market impact."""

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",  # Fast and cheap model
        "messages": [
            {
                "role": "system",
                "content": "You are a professional crypto sentiment analyst. Be concise and objective."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 500,
        "temperature": 0,
        "return_citations": True,
        "return_images": False
    }
    
    try:
        # Call Perplexity API
        response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        response_text = data['choices'][0]['message']['content']
        citations = data.get('citations', [])
        
        logger.info(f"Perplexity response: {response_text[:200]}...")
        
        # Extract sentiment
        sentiment = 'NEUTRAL'
        if 'BULLISH' in response_text.upper():
            sentiment = 'BULLISH'
        elif 'BEARISH' in response_text.upper():
            sentiment = 'BEARISH'
        
        # Extract confidence
        confidence = 50
        for line in response_text.split('\n'):
            if 'CONFIDENCE:' in line.upper():
                try:
                    confidence = int(''.join(filter(str.isdigit, line)))
                except:
                    confidence = 50
                break
        
        # Extract reasoning
        reasoning = "Analysis completed"
        for line in response_text.split('\n'):
            if 'REASONING:' in line.upper():
                reasoning = line.split(':', 1)[1].strip()
                break
        
        # Extract key points
        key_points = []
        in_key_points = False
        for line in response_text.split('\n'):
            if 'KEY_POINTS' in line.upper():
                in_key_points = True
                continue
            if in_key_points and line.strip().startswith('-'):
                key_points.append(line.strip()[1:].strip())
        
        result = {
            'sentiment': sentiment,
            'confidence': min(confidence, 100),
            'reasoning': reasoning,
            'key_points': key_points[:3],
            'sources': citations[:3]  # Perplexity bonus: real sources!
        }
        
        logger.info(f"Analysis result: {sentiment} ({confidence}%)")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Perplexity API: {e}")
        return {
            'sentiment': 'NEUTRAL',
            'confidence': 0,
            'reasoning': f'API Error: {str(e)}',
            'key_points': [],
            'sources': []
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'sentiment': 'NEUTRAL',
            'confidence': 0,
            'reasoning': f'Error: {str(e)}',
            'key_points': [],
            'sources': []
        }

# Test function
if __name__ == '__main__':
    # Test with example crypto news
    test_text = """
    Bitcoin surged past $50,000 today as institutional investors continue to 
    accumulate, with MicroStrategy announcing an additional $500M purchase. 
    Analysts predict further upside as ETF inflows remain strong.
    """
    
    print("Testing Perplexity sentiment analyzer...")
    print("=" * 60)
    result = analyze_sentiment(test_text)
    
    print(f"\n🎯 Sentiment: {result['sentiment']}")
    print(f"📊 Confidence: {result['confidence']}%")
    print(f"💡 Reasoning: {result['reasoning']}")
    print(f"\n📌 Key points:")
    for point in result['key_points']:
        print(f"  • {point}")
    
    if result['sources']:
        print(f"\n📚 Sources:")
        for source in result['sources']:
            print(f"  • {source}")
    
    print("=" * 60)
